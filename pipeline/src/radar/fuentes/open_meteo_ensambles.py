"""Open-Meteo Ensemble API: lluvia diaria por miembro de tres ensambles.

Sistemas (comprobados contra la API el 23-nov-2026):

======================  =========================  ========  ==================================
Sistema                 ``models=``                Miembros  Paso nativo de la lluvia
======================  =========================  ========  ==================================
ECMWF IFS ENS 0.25°     ``ecmwf_ifs025_ensemble``  51        3 h hasta +144 h; luego 6 h
ECMWF AIFS ENS 0.25°    ``ecmwf_aifs025_ensemble`` 51        6 h
NCEP GEFS 0.25°         ``ncep_gefs025``           31        3 h
======================  =========================  ========  ==================================

El miembro de control es la variable ``precipitation`` (aquí, miembro 0) y los demás
``precipitation_member01`` … ``precipitation_memberNN``. Se pide
``temporal_resolution=native``: cada valor es la lluvia del intervalo que termina en su
hora. Más allá de +144 h, IFS se sigue entregando cada 3 h, pero cada ventana de 6 h
se reparte a partes iguales en dos pasos; como esas ventanas terminan a las 00, 06, 12
y 18 UTC, el día de 12 a 12 UTC sigue siendo exacto (ver ``dias_12utc``).

Con ``elevation=nan`` la respuesta trae la altitud media de la celda del modelo en
lugar de la del punto pedido (modelo digital de 90 m), que es la que sirve para saber
si la celda representa bien al distrito. ``cell_selection=land`` (el valor por
defecto) prefiere celdas de tierra, pero cerca de la costa puede devolver una celda de
mar (altitud 0).

Cuota gratuita: menos de 10 000 llamadas al día, 5 000 por hora y 600 por minuto. Cada
punto pesa ``miembros / 10`` llamadas para hasta 14 días (IFS y AIFS 5.1, GEFS 3.1),
así que los puntos se agrupan en lotes y las llamadas se espacian con
``LimitadorCuota``. Los metadatos del modelo (``/data/<modelo>/static/meta.json``) no
cuentan contra la cuota y dicen la hora de inicialización de la última corrida.
"""

import json
import logging
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from itertools import pairwise
from typing import Any, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from radar.contratos.base import FechaUtc
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.dias_12utc import (
    HORA_CORTE,
    CorteInexacto,
    acumular_dias_12utc,
    primer_inicio_desde,
)
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

FUENTE = "Open-Meteo Ensemble API"
BASE = "https://ensemble-api.open-meteo.com/v1/ensemble"
META = "https://ensemble-api.open-meteo.com/data/{modelo}/static/meta.json"

DIAS = 7
"""Días de 12 a 12 UTC que se entregan por punto y sistema."""
DIAS_PEDIDOS = 9
"""``forecast_days``: la serie empieza a las 00 UTC de hoy; con 9 días caben 7 días
completos aunque la corrida sea de las 18 UTC. Hasta 14 días no cambia el coste."""
DIAS_REFERENCIA_COSTE = 14
COSTE_MAXIMO_LLAMADA = 500.0
"""Tope de coste de una sola llamada, por debajo de las 600 por minuto."""


class Sistema(StrEnum):
    """Sistema de ensambles. El valor es estable y se usa en registros y archivos."""

    IFS = "ecmwf_ifs"
    AIFS = "ecmwf_aifs"
    GEFS = "ncep_gefs"


@dataclass(frozen=True)
class DefinicionSistema:
    nombre: str
    modelo: str
    """Identificador ``models=`` de Open-Meteo."""
    miembros: int
    """Incluido el de control."""
    paso_h: int
    """Paso con que Open-Meteo entrega la serie nativa. Se exige regular: una fila
    perdida haría que el valor siguiente pareciera cubrir más horas de las que cubre."""

    @property
    def variables(self) -> tuple[str, ...]:
        """Variables de la respuesta en orden de miembro: control primero."""
        perturbados = [f"precipitation_member{i:02d}" for i in range(1, self.miembros)]
        return ("precipitation", *perturbados)


SISTEMAS: Mapping[Sistema, DefinicionSistema] = {
    Sistema.IFS: DefinicionSistema("ECMWF IFS ENS 0.25°", "ecmwf_ifs025_ensemble", 51, 3),
    Sistema.AIFS: DefinicionSistema("ECMWF AIFS ENS 0.25°", "ecmwf_aifs025_ensemble", 51, 6),
    Sistema.GEFS: DefinicionSistema("NCEP GEFS 0.25°", "ncep_gefs025", 31, 3),
}


# --- Modelo de datos interno (no es un contrato publicado) ---------------------------


class _Modelo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Punto(_Modelo):
    """Lugar para el que se pide el pronóstico."""

    id: str = Field(min_length=1)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class Celda(_Modelo):
    """Celda que Open-Meteo usó de verdad para un punto; puede no coincidir con él."""

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    altitud_m: float | None = Field(description="Altitud media de la celda en el modelo.")


class DiaLluvia(_Modelo):
    """Lluvia de un día de 12 a 12 UTC por miembro, sin mezclar ni promediar."""

    inicio: FechaUtc = Field(description="12:00 UTC del día; termina 24 h después.")
    lluvia_mm: tuple[float | None, ...] = Field(
        min_length=1,
        description="Por miembro, el 0 es el de control. None: el miembro no cuenta ese día.",
    )
    miembros_validos: int = Field(ge=0)

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if (self.inicio.hour, self.inicio.minute, self.inicio.second) != (HORA_CORTE, 0, 0):
            raise ValueError("el día debe empezar a las 12:00 UTC")
        if any(v is not None and v < 0 for v in self.lluvia_mm):
            raise ValueError("la lluvia no puede ser negativa")
        if self.miembros_validos != sum(v is not None for v in self.lluvia_mm):
            raise ValueError("miembros_validos no coincide con los valores presentes")
        return self


class SeriePunto(_Modelo):
    punto: Punto
    celda: Celda
    dias: tuple[DiaLluvia, ...] = Field(min_length=DIAS, max_length=DIAS)

    @model_validator(mode="after")
    def _dias_seguidos(self) -> Self:
        if any(b.inicio - a.inicio != timedelta(days=1) for a, b in pairwise(self.dias)):
            raise ValueError("los días deben ser consecutivos")
        return self


class PronosticoSistema(_Modelo):
    """Lo entregado por un sistema para todos los puntos pedidos."""

    sistema: Sistema
    modelo: str
    miembros: int = Field(ge=1)
    inicializacion: FechaUtc | None = Field(
        description="Hora de inicio de la corrida; None si no se pudo saber con certeza."
    )
    primer_dia: FechaUtc
    puntos: tuple[SeriePunto, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        for serie in self.puntos:
            if serie.dias[0].inicio != self.primer_dia:
                raise ValueError(f"{serie.punto.id}: no empieza en primer_dia")
            if any(len(d.lluvia_mm) != self.miembros for d in serie.dias):
                raise ValueError(
                    f"{serie.punto.id}: número de miembros distinto de {self.miembros}"
                )
        return self


class EnsamblesLluvia(_Modelo):
    """Resultado de una consulta: cada sistema por separado.

    Un sistema está en uno solo de ``sistemas`` (entregado), ``fallos`` (motivo) o
    ``sin_corrida_nueva`` (la corrida ya se tenía y no se descargó).
    """

    obtenido_en: FechaUtc
    sistemas: dict[Sistema, PronosticoSistema]
    fallos: dict[Sistema, str]
    sin_corrida_nueva: dict[Sistema, FechaUtc]

    @model_validator(mode="after")
    def _disjuntos(self) -> Self:
        claves = [*self.sistemas, *self.fallos, *self.sin_corrida_nueva]
        if len(claves) != len(set(claves)):
            raise ValueError("un sistema no puede estar en dos estados a la vez")
        if any(p.sistema != s for s, p in self.sistemas.items()):
            raise ValueError("clave de sistema inconsistente")
        return self


# --- Cuota -----------------------------------------------------------------------------


def coste_llamada(puntos: int, miembros: int, dias: int = DIAS_PEDIDOS) -> float:
    """Llamadas que descuenta Open-Meteo: ``max(1, V/10 · max(1, D/14))`` por punto.

    En ensambles cada miembro cuenta como una variable (documentación de límites de
    Open-Meteo, comprobado con la cabecera ``X-RateLimit-Cost``).
    """
    por_punto = max(1.0, miembros / 10 * max(1.0, dias / DIAS_REFERENCIA_COSTE))
    return puntos * por_punto


def puntos_por_llamada(miembros: int, tope: float = COSTE_MAXIMO_LLAMADA) -> int:
    return max(1, int(tope // coste_llamada(1, miembros)))


@dataclass
class LimitadorCuota:
    """Espera lo necesario para no pasar de los límites por ventana de tiempo.

    Solo conoce el consumo de este proceso; la cuota de Open-Meteo es por IP. Por eso
    los límites van con margen: 540 de 600 por minuto y 4 500 de 5 000 por hora.
    """

    limites: tuple[tuple[float, float], ...] = ((60.0, 540.0), (3600.0, 4500.0))
    reloj: Callable[[], float] = field(default=time.monotonic, repr=False)
    esperar: Callable[[float], None] = field(default=time.sleep, repr=False)
    _gastos: list[tuple[float, float]] = field(default_factory=list, repr=False)

    def _espera_necesaria(self, coste: float, ahora: float) -> float:
        espera = 0.0
        for ventana, limite in self.limites:
            recientes = [(t, c) for t, c in self._gastos if t > ahora - ventana]
            usado = sum(c for _, c in recientes)
            for t, c in recientes:
                if usado + coste <= limite:
                    break
                usado -= c
                espera = max(espera, t + ventana - ahora)
        return espera

    def reservar(self, coste: float) -> None:
        """Bloquea hasta que ``coste`` cabe en todas las ventanas y lo anota."""
        if any(coste > limite for _, limite in self.limites):
            raise ValueError(f"una llamada de coste {coste} no cabe en ningún minuto")
        while (espera := self._espera_necesaria(coste, self.reloj())) > 0:
            registro.info("%s: espera de %.0f s para respetar la cuota", FUENTE, espera)
            self.esperar(espera)
        ahora = self.reloj()
        mayor = max(v for v, _ in self.limites)
        self._gastos = [(t, c) for t, c in self._gastos if t > ahora - mayor]
        self._gastos.append((ahora, coste))


# --- Interpretación de respuestas ------------------------------------------------------


def url_consulta(definicion: DefinicionSistema, puntos: Sequence[Punto]) -> str:
    parametros = {
        "latitude": ",".join(f"{p.latitud:.4f}" for p in puntos),
        "longitude": ",".join(f"{p.longitud:.4f}" for p in puntos),
        "hourly": "precipitation",
        "models": definicion.modelo,
        "forecast_days": str(DIAS_PEDIDOS),
        "temporal_resolution": "native",
        "timeformat": "unixtime",
        "cell_selection": "land",
        "elevation": ",".join("nan" for _ in puntos),
    }
    return str(httpx.URL(BASE, params=parametros))


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return None
    numero = float(valor)
    return numero if math.isfinite(numero) else None


def _fechas(tiempos: Any, desfase: Any, fuente: str) -> list[datetime]:
    if not isinstance(tiempos, list) or not tiempos:
        raise FuenteNoDisponible(fuente, "respuesta sin horas")
    fechas: list[datetime] = []
    for t in tiempos:
        if isinstance(t, int) and not isinstance(t, bool):
            fechas.append(datetime.fromtimestamp(t, UTC))
            continue
        try:
            fecha = datetime.fromisoformat(t) if isinstance(t, str) else None
        except ValueError:
            fecha = None
        if fecha is None:
            raise FuenteNoDisponible(fuente, f"hora no reconocida: {t!r}")
        if fecha.tzinfo is None:
            # Open-Meteo escribe la hora local sin zona y declara el desfase aparte.
            if not isinstance(desfase, int) or isinstance(desfase, bool):
                raise FuenteNoDisponible(fuente, f"hora sin zona horaria: {t!r}")
            fecha = fecha.replace(tzinfo=timezone(timedelta(seconds=desfase)))
        fechas.append(fecha.astimezone(UTC))
    return fechas


def interpretar_respuesta(
    texto: str, sistema: Sistema, puntos: Sequence[Punto], primer_dia: datetime
) -> list[SeriePunto]:
    """Convierte la respuesta de un lote de puntos en series diarias. Sin red."""
    definicion = SISTEMAS[sistema]
    fuente = f"{FUENTE} ({definicion.modelo})"
    try:
        datos = json.loads(texto)
    except ValueError as error:
        raise FuenteNoDisponible(fuente, "la respuesta no es JSON") from error
    if isinstance(datos, dict) and datos.get("error"):
        raise FuenteNoDisponible(fuente, f"error de la API: {datos.get('reason', 'sin motivo')}")
    lugares = [datos] if isinstance(datos, dict) else datos
    if not isinstance(lugares, list) or len(lugares) != len(puntos):
        recibidos = len(lugares) if isinstance(lugares, list) else 0
        raise FuenteNoDisponible(
            fuente, f"respuesta incompleta: {recibidos} lugares para {len(puntos)} puntos"
        )

    series: list[SeriePunto] = []
    for punto, lugar in zip(puntos, lugares, strict=True):
        try:
            series.append(_serie(fuente, definicion, punto, lugar, primer_dia))
        except ValidationError as error:
            raise FuenteNoDisponible(fuente, f"{punto.id}: datos inválidos: {error}") from error
    return series


def _serie(
    fuente: str,
    definicion: DefinicionSistema,
    punto: Punto,
    lugar: Any,
    primer_dia: datetime,
) -> SeriePunto:
    if not isinstance(lugar, dict) or not isinstance(lugar.get("hourly"), dict):
        raise FuenteNoDisponible(fuente, f"{punto.id}: lugar sin datos horarios")
    latitud, longitud = _numero(lugar.get("latitude")), _numero(lugar.get("longitude"))
    if latitud is None or longitud is None:
        raise FuenteNoDisponible(fuente, f"{punto.id}: la respuesta no dice qué celda usó")
    celda = Celda(latitud=latitud, longitud=longitud, altitud_m=_numero(lugar.get("elevation")))

    horario: dict[str, Any] = lugar["hourly"]
    fines = _fechas(horario.get("time"), lugar.get("utc_offset_seconds"), fuente)
    paso = timedelta(hours=definicion.paso_h)
    if any(b - a != paso for a, b in pairwise(fines)):
        raise FuenteNoDisponible(
            fuente, f"{punto.id}: las horas no van cada {definicion.paso_h} h como se esperaba"
        )
    faltan = [v for v in definicion.variables if not isinstance(horario.get(v), list)]
    if faltan:
        raise FuenteNoDisponible(
            fuente, f"{punto.id}: respuesta incompleta, faltan {len(faltan)} miembros"
        )

    por_miembro: list[dict[datetime, float | None]] = []
    for variable in definicion.variables:
        valores = [_numero(v) for v in horario[variable]]
        if len(valores) != len(fines):
            raise FuenteNoDisponible(fuente, f"{punto.id}: {variable} no tiene todas las horas")
        try:
            por_miembro.append(acumular_dias_12utc(fines, valores))
        except CorteInexacto as error:
            raise FuenteNoDisponible(fuente, f"{punto.id}: {error}") from error

    inicios = [d for d in por_miembro[0] if d >= primer_dia][:DIAS]
    if len(inicios) < DIAS or inicios[0] != primer_dia:
        raise FuenteNoDisponible(
            fuente,
            f"{punto.id}: solo {len(inicios)} días completos desde {primer_dia.isoformat()}",
        )
    dias = []
    for inicio in inicios:
        lluvia = tuple(miembro[inicio] for miembro in por_miembro)
        dias.append(
            DiaLluvia(
                inicio=inicio,
                lluvia_mm=lluvia,
                miembros_validos=sum(v is not None for v in lluvia),
            )
        )
    nulos = sum(definicion.miembros - d.miembros_validos for d in dias)
    if nulos:
        registro.warning("%s: %s: %d miembro-días sin dato", fuente, punto.id, nulos)
    return SeriePunto(punto=punto, celda=celda, dias=tuple(dias))


def interpretar_meta(texto: str) -> datetime:
    """Hora de inicialización de la última corrida a partir de ``meta.json``."""
    try:
        segundos = json.loads(texto)["last_run_initialisation_time"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError("meta.json sin last_run_initialisation_time") from error
    if isinstance(segundos, bool) or not isinstance(segundos, int) or segundos <= 0:
        raise ValueError(f"inicialización no reconocida: {segundos!r}")
    return datetime.fromtimestamp(segundos, UTC)


# --- Adaptador -------------------------------------------------------------------------


class FuenteEnsamblesOpenMeteo:
    """Lluvia diaria por miembro de IFS, AIFS y GEFS para una lista de puntos.

    Cada sistema se pide y valida por separado: si uno falla o llega incompleto, los
    otros se entregan y el fallo queda en ``EnsamblesLluvia.fallos``. Solo si no se
    obtiene nada se lanza ``FuenteNoDisponible``.

    ``corridas_conocidas`` evita volver a descargar un sistema cuya última corrida ya
    se tiene: se consulta antes su ``meta.json``, que no gasta cuota.
    """

    def __init__(
        self,
        puntos: Sequence[Punto],
        *,
        sistemas: Sequence[Sistema] = tuple(Sistema),
        corridas_conocidas: Mapping[Sistema, datetime] | None = None,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        limitador: LimitadorCuota | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not puntos:
            raise ValueError("hace falta al menos un punto")
        if len({p.id for p in puntos}) != len(puntos):
            raise ValueError("los identificadores de punto deben ser únicos")
        self._puntos = tuple(puntos)
        self._sistemas = tuple(dict.fromkeys(sistemas))
        self._conocidas = {s: f.astimezone(UTC) for s, f in (corridas_conocidas or {}).items()}
        self._cliente = cliente
        self._politica = politica
        self._limitador = limitador or LimitadorCuota()
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "open-meteo-ensambles"

    def coste_estimado(self) -> float:
        """Llamadas de cuota que gasta una consulta completa de todos los sistemas."""
        return sum(coste_llamada(len(self._puntos), SISTEMAS[s].miembros) for s in self._sistemas)

    def inicializacion(self, sistema: Sistema) -> datetime | None:
        """Última corrida publicada del sistema, o None si no se puede saber."""
        modelo = SISTEMAS[sistema].modelo
        try:
            texto = descargar_texto(
                f"{FUENTE} (meta {modelo})",
                META.format(modelo=modelo),
                cliente=self._cliente,
                politica=self._politica,
            )
            return interpretar_meta(texto)
        except (FuenteNoDisponible, ValueError) as error:
            registro.warning("%s: no se pudo saber la corrida de %s: %s", FUENTE, modelo, error)
            return None

    def obtener(self) -> EnsamblesLluvia:
        entregados: dict[Sistema, PronosticoSistema] = {}
        fallos: dict[Sistema, str] = {}
        sin_cambio: dict[Sistema, datetime] = {}
        for sistema in self._sistemas:
            try:
                inicio = self.inicializacion(sistema)
                if inicio is not None and self._conocidas.get(sistema) == inicio:
                    registro.info("%s: %s sin corrida nueva (%s)", FUENTE, sistema, inicio)
                    sin_cambio[sistema] = inicio
                    continue
                entregados[sistema] = self._obtener_sistema(sistema, inicio)
            except FuenteNoDisponible as error:
                registro.warning("%s: %s falló: %s", FUENTE, sistema, error)
                fallos[sistema] = str(error)
        if not entregados and not sin_cambio:
            resumen = "; ".join(f"{s}: {m}" for s, m in fallos.items())
            raise FuenteNoDisponible(FUENTE, f"fallaron todos los sistemas ({resumen})")
        return EnsamblesLluvia(
            obtenido_en=self._ahora(),
            sistemas=entregados,
            fallos=fallos,
            sin_corrida_nueva=sin_cambio,
        )

    def _obtener_sistema(self, sistema: Sistema, inicio: datetime | None) -> PronosticoSistema:
        definicion = SISTEMAS[sistema]
        tam = puntos_por_llamada(definicion.miembros)
        lotes = [self._puntos[i : i + tam] for i in range(0, len(self._puntos), tam)]
        textos: list[str] = []
        for lote in lotes:
            self._limitador.reservar(coste_llamada(len(lote), definicion.miembros))
            textos.append(
                descargar_texto(
                    f"{FUENTE} ({definicion.modelo})",
                    url_consulta(definicion, lote),
                    cliente=self._cliente,
                    politica=self._politica,
                )
            )
        if inicio is not None:
            despues = self.inicializacion(sistema)
            if despues is None:
                inicio = None  # no se puede confirmar a qué corrida pertenecen los datos
            elif despues != inicio:
                # Los lotes podrían mezclar dos corridas: mejor nada que datos incoherentes.
                raise FuenteNoDisponible(
                    f"{FUENTE} ({definicion.modelo})",
                    f"la corrida cambió durante la descarga ({inicio.isoformat()} →"
                    f" {despues.isoformat()})",
                )
        primer_dia = primer_inicio_desde(inicio if inicio is not None else self._ahora())
        series = [
            serie
            for lote, texto in zip(lotes, textos, strict=True)
            for serie in interpretar_respuesta(texto, sistema, lote, primer_dia)
        ]
        try:
            return PronosticoSistema(
                sistema=sistema,
                modelo=definicion.modelo,
                miembros=definicion.miembros,
                inicializacion=inicio,
                primer_dia=primer_dia,
                puntos=tuple(series),
            )
        except ValidationError as error:  # pragma: no cover - las series ya se validaron
            raise FuenteNoDisponible(FUENTE, f"{sistema}: datos inválidos: {error}") from error
