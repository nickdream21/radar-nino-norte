"""Producto ``lluvia/distritos.json`` (M1 v1), su estado entre ejecuciones y el archivo.

Cada hora:

1. Se consulta ``meta.json`` de cada sistema (no gasta cuota). Se descarga solo una
   corrida nueva que esté en el plan: 00 UTC de los tres sistemas y 12 UTC de IFS.
   Una corrida fuera del plan solo se descarga si no hay dato del sistema o si el que
   hay tiene más de 24 h de retraso respecto a la última (recuperación tras un fallo).
2. Lo descargado se guarda como conteos por celda y día en
   ``lluvia/estado-ensambles.json``, dentro de la propia publicación: así una corrida
   de IFS de 12 UTC se mezcla con AIFS y GEFS de 00 UTC sin volver a descargarlos.
3. Se eligen las corridas de la mezcla (``modelos.lluvia.elegir_corridas``). Si son
   las mismas del producto anterior, el producto no se toca. Sin ECMWF no se emite y
   se conserva el anterior con su antigüedad.
4. Si se descargó algo se escribe un archivo comprimido con los valores por miembro
   en ``archivo-pendiente/``; el flujo de ingesta lo sube a GitHub Releases (ADR 0006).
"""

import gzip
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import ValidationError

from radar import __version__
from radar.contratos import CatalogoDistritos, ProductoPublicado
from radar.contratos.base import Contrato
from radar.contratos.lluvia import (
    ArchivoLluvia,
    CeldaArchivada,
    CeldaModelo,
    CorridaUsada,
    CriteriosNiveles,
    DiaArchivado,
    DiaDistritoLluvia,
    DiaPronostico,
    DistritoLluvia,
    LluviaDistritos,
    MetodoLluvia,
    PeriodoTendencia,
    SistemaArchivado,
    UmbralesZona,
)
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.dias_12utc import UN_DIA
from radar.fuentes.http import PoliticaReintentos
from radar.fuentes.open_meteo_ensambles import (
    EnsamblesLluvia,
    FuenteEnsamblesOpenMeteo,
    LimitadorCuota,
    PronosticoSistema,
    Punto,
    Sistema,
)
from radar.modelos import lluvia as m1
from radar.publicacion.escritor import escribir_bytes, escribir_json

registro = logging.getLogger(__name__)

ID_PRODUCTO = "lluvia-distritos"
RUTA_PRODUCTO = "lluvia/distritos.json"
RUTA_ESTADO = "lluvia/estado-ensambles.json"
CARPETA_ARCHIVO = "archivo-pendiente"
PREFIJO_ARCHIVO = "lluvia-distritos-"
MAXIMO_PENDIENTES = 20
"""Si la subida a Releases falla muchas veces seguidas, no se acumulan sin límite."""
FUENTE = (
    "Open-Meteo Ensemble API (ECMWF IFS ENS, ECMWF AIFS ENS, NCEP GEFS), CC BY 4.0;"
    " M1 v1 de Radar Niño Norte"
)

VIGENCIA_MIN = 30 * 60
"""30 horas, medidas desde la corrida más reciente usada.

El producto se renueva con IFS de 00 y de 12 UTC, que Open-Meteo publica unas 12 h
después de su hora de inicio. Con la ingesta horaria, la corrida más reciente tiene
normalmente entre 12 y 25 h. Si se pierde una corrida, llega a 36 h. Con 30 h la web
marca el producto como antiguo cuando falta una actualización, pero no por el retraso
habitual del cron ni de Open-Meteo.
"""

HORAS_PLAN: Mapping[Sistema, frozenset[int]] = {
    Sistema.IFS: frozenset({0, 12}),
    Sistema.AIFS: frozenset({0}),
    Sistema.GEFS: frozenset({0}),
}
"""Horas UTC de corrida que se descargan: unas 2 150 llamadas al día con 117 celdas."""
RECUPERACION = timedelta(hours=24)


class EstadoEnsambles(Contrato):
    """Estado interno entre ejecuciones; no es un producto para la web."""

    version: Literal[1] = 1
    umbrales_conteo_mm: list[float]
    sistemas: list[SistemaArchivado]


class ProveedorEnsambles(Protocol):
    def inicializacion(self, sistema: Sistema) -> datetime | None: ...

    def descargar(
        self, sistemas: Sequence[Sistema], conocidas: Mapping[Sistema, datetime]
    ) -> EnsamblesLluvia: ...


class ProveedorOpenMeteo:
    """``ProveedorEnsambles`` real sobre ``FuenteEnsamblesOpenMeteo``."""

    def __init__(
        self,
        puntos: Sequence[Punto],
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        limitador: LimitadorCuota | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._puntos = tuple(puntos)
        self._cliente = cliente
        self._politica = politica
        self._limitador = limitador or LimitadorCuota()
        self._ahora = ahora

    def _fuente(
        self,
        sistemas: Sequence[Sistema] = tuple(Sistema),
        conocidas: Mapping[Sistema, datetime] | None = None,
    ) -> FuenteEnsamblesOpenMeteo:
        return FuenteEnsamblesOpenMeteo(
            self._puntos,
            sistemas=sistemas,
            corridas_conocidas=conocidas,
            limitador=self._limitador,
            ahora=self._ahora,
            cliente=self._cliente,
            politica=self._politica,
        )

    def inicializacion(self, sistema: Sistema) -> datetime | None:
        return self._fuente().inicializacion(sistema)

    def descargar(
        self, sistemas: Sequence[Sistema], conocidas: Mapping[Sistema, datetime]
    ) -> EnsamblesLluvia:
        return self._fuente(sistemas, conocidas).obtener()


@dataclass(frozen=True)
class FuentesLluvia:
    catalogo: CatalogoDistritos
    proveedor: ProveedorEnsambles


# --- Celdas ------------------------------------------------------------------------------


def nodo(latitud: float, longitud: float) -> tuple[float, float]:
    """Nodo de la rejilla de 0.25° más cercano."""
    return round(latitud * 4) / 4, round(longitud * 4) / 4


def id_nodo(latitud: float, longitud: float) -> str:
    lat, lon = nodo(latitud, longitud)
    return f"{lat:.2f},{lon:.2f}"


def puntos_catalogo(catalogo: CatalogoDistritos) -> list[Punto]:
    """Un punto por nodo de 0.25° con alguna capital: cada celda se pide una sola vez."""
    nodos = {nodo(d.capital.latitud, d.capital.longitud) for d in catalogo.distritos}
    return [Punto(id=id_nodo(lat, lon), latitud=lat, longitud=lon) for lat, lon in sorted(nodos)]


# --- Plan de descarga --------------------------------------------------------------------


def debe_descargar(sistema: Sistema, ultima: datetime, conocida: datetime | None) -> bool:
    """Si la última corrida publicada de ``sistema`` merece gastar cuota."""
    if conocida is None:
        return True
    if ultima <= conocida:
        return False
    return ultima.hour in HORAS_PLAN[sistema] or ultima - conocida > RECUPERACION


# --- Estado y archivo --------------------------------------------------------------------


def archivar_sistema(pronostico: PronosticoSistema, obtenido_en: datetime) -> SistemaArchivado:
    """Valores por miembro y conteos de un sistema recién descargado."""
    if pronostico.inicializacion is None:
        raise ValueError("no se archiva una corrida de hora desconocida")
    celdas = []
    for serie in pronostico.puntos:
        dias = []
        for dia in serie.dias:
            conteo = m1.contar(dia.lluvia_mm)
            dias.append(
                DiaArchivado(
                    inicio=dia.inicio,
                    validos=conteo.validos,
                    alcanzan=list(conteo.alcanzan),
                    lluvia_mm=list(dia.lluvia_mm),
                )
            )
        celdas.append(
            CeldaArchivada(
                id=serie.punto.id,
                latitud=serie.celda.latitud,
                longitud=serie.celda.longitud,
                altitud_m=serie.celda.altitud_m,
                dias=dias,
            )
        )
    return SistemaArchivado(
        sistema=pronostico.sistema.value,
        modelo=pronostico.modelo,
        miembros=pronostico.miembros,
        inicializacion=pronostico.inicializacion,
        primer_dia=pronostico.primer_dia,
        obtenido_en=obtenido_en,
        celdas=celdas,
    )


def sin_valores(sistema: SistemaArchivado) -> SistemaArchivado:
    """El mismo sistema solo con conteos, para el estado entre ejecuciones."""
    celdas = [
        c.model_copy(update={"dias": [d.model_copy(update={"lluvia_mm": None}) for d in c.dias]})
        for c in sistema.celdas
    ]
    return sistema.model_copy(update={"celdas": celdas})


def leer_estado(ruta: Path) -> dict[Sistema, SistemaArchivado]:
    """Último dato de cada sistema; vacío si no hay estado utilizable."""
    if not ruta.exists():
        return {}
    try:
        estado = EstadoEnsambles.model_validate_json(ruta.read_bytes())
    except (OSError, ValidationError) as error:
        registro.warning("No se puede reutilizar %s: %s", ruta, error)
        return {}
    if tuple(estado.umbrales_conteo_mm) != m1.UMBRALES_CONTEO_MM:
        registro.warning("%s tiene otros umbrales: se descartan sus conteos", ruta)
        return {}
    return {Sistema(s.sistema): s for s in estado.sistemas}


def leer_producto(ruta: Path) -> LluviaDistritos | None:
    if not ruta.exists():
        return None
    try:
        return LluviaDistritos.model_validate_json(ruta.read_bytes())
    except (OSError, ValidationError) as error:
        registro.warning("No se puede reutilizar %s: %s", ruta, error)
        return None


def nombre_archivo(generado_en: datetime) -> str:
    return f"{PREFIJO_ARCHIVO}{generado_en.astimezone(UTC):%Y%m%dT%H%M%SZ}.json.gz"


def escribir_archivo(archivo: ArchivoLluvia, carpeta: Path) -> Path:
    """Escribe el archivo comprimido (sin fecha en la cabecera gzip: reproducible)."""
    ruta = carpeta / nombre_archivo(archivo.generado_en)
    contenido = gzip.compress(archivo.model_dump_json().encode("utf-8"), mtime=0)
    escribir_bytes(contenido, ruta)
    pendientes = sorted(carpeta.glob(f"{PREFIJO_ARCHIVO}*.json.gz"))
    for sobrante in pendientes[:-MAXIMO_PENDIENTES]:
        registro.error("Archivo nunca subido a Releases, se descarta: %s", sobrante.name)
        sobrante.unlink()
    return ruta


def leer_archivo(ruta: Path) -> ArchivoLluvia:
    return ArchivoLluvia.model_validate_json(gzip.decompress(ruta.read_bytes()))


# --- Producto ----------------------------------------------------------------------------


def metodo() -> MetodoLluvia:
    c = m1.CRITERIOS
    return MetodoLluvia(
        modelo="m1-v1",
        pesos={s.value: float(p) for s, p in m1.PESOS.items()},
        umbrales_mm={
            z: UmbralesZona(t1_mm=t1, t2_mm=t2, t3_mm=t3)
            for z, (t1, t2, t3) in m1.UMBRALES_MM.items()
        },
        niveles=CriteriosNiveles(
            amarillo_t1=c.amarillo_t1,
            naranja_t2=c.naranja_t2,
            naranja_t3=c.naranja_t3,
            rojo_t3=c.rojo_t3,
            rojo_t2=c.rojo_t2,
        ),
        tope_tendencia=m1.TOPE_TENDENCIA,
        desfase_maximo_h=int(m1.DESFASE_MAXIMO.total_seconds() // 3600),
        altitud_sierra_m=m1.ALTITUD_SIERRA_M,
        diferencia_altitud_costa_m=m1.DIFERENCIA_ALTITUD_COSTA_M,
        diferencia_altitud_sierra_m=m1.DIFERENCIA_ALTITUD_SIERRA_M,
    )


def corridas_de(producto: LluviaDistritos) -> dict[Sistema, datetime]:
    return {Sistema(c.sistema): c.inicializacion for c in producto.corridas}


def hay_que_emitir(anterior: LluviaDistritos | None, elegidas: Mapping[Sistema, datetime]) -> bool:
    """Se emite si no hay producto, si cambió el método o si entra una corrida más nueva.

    Así una corrida que queda fuera de la mezcla (por ejemplo GEFS a más de 12 h de la
    última ECMWF) no hace perder la que se usaba antes de ese mismo sistema.
    """
    if anterior is None or anterior.metodo != metodo():
        return True
    publicadas = corridas_de(anterior)
    return any(s not in publicadas or t > publicadas[s] for s, t in elegidas.items())


def construir_producto(
    catalogo: CatalogoDistritos, estado: Mapping[Sistema, SistemaArchivado], ahora: datetime
) -> LluviaDistritos | None:
    """Mezcla las corridas elegidas del estado; ``None`` si no hay ninguna de ECMWF."""
    elegidas = m1.elegir_corridas({s: a.inicializacion for s, a in estado.items()})
    ancla = m1.corrida_ancla(elegidas or {})
    if elegidas is None or ancla is None:
        return None
    usados = [s for s in Sistema if s in elegidas]
    inicios = [estado[ancla].primer_dia + k * UN_DIA for k in range(m1.DIAS_PRONOSTICO)]
    celdas_por_sistema = {s: {c.id: c for c in estado[s].celdas} for s in usados}
    dias_por_celda = {
        s: {c.id: {d.inicio: d for d in c.dias} for c in estado[s].celdas} for s in usados
    }

    def conteo(s: Sistema, celda: str, inicio: datetime) -> m1.Conteo | None:
        dia = dias_por_celda[s].get(celda, {}).get(inicio)
        return None if dia is None else m1.Conteo(dia.validos, tuple(dia.alcanzan))

    celdas: list[CeldaModelo] = []
    indice_celda: dict[str, int] = {}
    distritos: list[DistritoLluvia] = []
    for distrito in catalogo.distritos:
        capital = distrito.capital
        nid = id_nodo(capital.latitud, capital.longitud)
        propias = [c for s in usados if (c := celdas_por_sistema[s].get(nid)) is not None]
        if propias and nid not in indice_celda:
            principal = propias[0]  # IFS si está, luego AIFS y GEFS
            indice_celda[nid] = len(celdas)
            celdas.append(
                CeldaModelo(
                    latitud=principal.latitud,
                    longitud=principal.longitud,
                    altitud_m=None if principal.altitud_m is None else round(principal.altitud_m),
                )
            )
        dias = [
            m1.dia_distrito(
                {s: conteo(s, nid, inicio) for s in usados}, m1.UMBRALES_MM[distrito.zona]
            )
            for inicio in inicios
        ]
        distritos.append(
            DistritoLluvia(
                ubigeo=distrito.ubigeo,
                zona=distrito.zona,
                celda=indice_celda.get(nid),
                mal_representado=m1.mal_representado(
                    capital.altitud_m, [c.altitud_m for c in propias]
                ),
                dias=[
                    DiaDistritoLluvia(
                        nivel=d.nivel,
                        probabilidades=None if d.porcentajes is None else list(d.porcentajes),
                    )
                    for d in dias[: m1.DIAS_SEMAFORO]
                ],
                tendencia=m1.tendencia([d.nivel for d in dias[m1.DIAS_SEMAFORO :]]),
            )
        )

    pesos = m1.pesos_normalizados(usados)
    return LluviaDistritos(
        generado_en=ahora,
        verificacion="sin_verificar",
        metodo=metodo(),
        corridas=[
            CorridaUsada(
                sistema=s.value,
                modelo=estado[s].modelo,
                inicializacion=estado[s].inicializacion,
                miembros=estado[s].miembros,
                peso=round(float(pesos[s]), 4),
            )
            for s in usados
        ],
        dias=[
            DiaPronostico(
                inicio=inicio,
                fin=inicio + UN_DIA,
                sistemas=[
                    s.value for s in usados if any(inicio in d for d in dias_por_celda[s].values())
                ],
            )
            for inicio in inicios[: m1.DIAS_SEMAFORO]
        ],
        tendencia=PeriodoTendencia(
            inicio=inicios[m1.DIAS_SEMAFORO], fin=inicios[-1] + UN_DIA, confianza="baja"
        ),
        celdas=celdas,
        distritos=distritos,
    )


def entrada_manifiesto(producto: LluviaDistritos) -> ProductoPublicado:
    return ProductoPublicado(
        id=ID_PRODUCTO,
        ruta=RUTA_PRODUCTO,
        fuente=FUENTE,
        actualizado_en=max(c.inicializacion for c in producto.corridas),
        vigencia_min=VIGENCIA_MIN,
    )


def _descargar(
    proveedor: ProveedorEnsambles, estado: Mapping[Sistema, SistemaArchivado]
) -> dict[Sistema, SistemaArchivado]:
    """Descarga las corridas nuevas que tocan según el plan."""
    pedir: list[Sistema] = []
    for sistema in Sistema:
        conocida = estado[sistema].inicializacion if sistema in estado else None
        ultima = proveedor.inicializacion(sistema)
        if ultima is None:
            registro.warning("Lluvia: no se sabe la última corrida de %s", sistema)
        elif debe_descargar(sistema, ultima, conocida):
            pedir.append(sistema)
        else:
            registro.info("Lluvia: %s sin corrida que descargar (última %s)", sistema, ultima)
    if not pedir:
        return {}
    conocidas = {s: estado[s].inicializacion for s in pedir if s in estado}
    try:
        resultado = proveedor.descargar(pedir, conocidas)
    except FuenteNoDisponible as error:
        registro.error("Lluvia: no se pudo descargar ningún sistema: %s", error)
        return {}
    nuevos: dict[Sistema, SistemaArchivado] = {}
    for sistema, pronostico in resultado.sistemas.items():
        if pronostico.inicializacion is None:
            registro.warning(
                "Lluvia: %s llegó sin hora de corrida confirmada; se descarta", sistema
            )
            continue
        if pronostico.inicializacion.hour not in HORAS_PLAN[sistema]:
            registro.info(
                "Lluvia: %s corrida %s fuera del plan", sistema, pronostico.inicializacion
            )
        nuevos[sistema] = archivar_sistema(pronostico, resultado.obtenido_en)
    return nuevos


def publicar_lluvia(
    carpeta: Path,
    fuentes: FuentesLluvia,
    ahora: datetime,
    *,
    carpeta_archivo: Path | None = None,
    commit: str | None = None,
) -> ProductoPublicado | None:
    """Actualiza ``lluvia/distritos.json`` si hay corridas nuevas y devuelve su entrada.

    Devuelve ``None`` si no hay producto nuevo ni anterior válido.
    """
    ruta = carpeta / RUTA_PRODUCTO
    anterior = leer_producto(ruta)
    estado = leer_estado(carpeta / RUTA_ESTADO)

    descargados = _descargar(fuentes.proveedor, estado)
    if descargados:
        estado = {**estado, **{s: sin_valores(a) for s, a in descargados.items()}}
        escribir_json(
            EstadoEnsambles(
                umbrales_conteo_mm=list(m1.UMBRALES_CONTEO_MM),
                sistemas=[estado[s] for s in Sistema if s in estado],
            ),
            carpeta / RUTA_ESTADO,
            compacto=True,
        )

    nuevo: LluviaDistritos | None = None
    elegidas = m1.elegir_corridas({s: a.inicializacion for s, a in estado.items()})
    if elegidas is None:
        registro.warning("Lluvia: sin corrida de ECMWF no se emite pronóstico nuevo")
    elif not hay_que_emitir(anterior, elegidas):
        registro.info("Lluvia: ninguna corrida más nueva que las publicadas; no cambia")
    else:
        nuevo = construir_producto(fuentes.catalogo, estado, ahora)
        if nuevo is not None:
            escribir_json(nuevo, ruta, compacto=True)
            registro.info(
                "Lluvia: pronóstico emitido con %s",
                ", ".join(f"{c.sistema} {c.inicializacion:%Y-%m-%d %H}Z" for c in nuevo.corridas),
            )

    if descargados:
        archivo = ArchivoLluvia(
            formato="radar-nino-norte/archivo-lluvia",
            version_formato=1,
            generado_en=ahora,
            version_pipeline=__version__,
            commit=commit,
            hora_corte_utc=12,
            umbrales_conteo_mm=list(m1.UMBRALES_CONTEO_MM),
            descargados=[s.value for s in Sistema if s in descargados],
            sistemas=[descargados.get(s) or estado[s] for s in Sistema if s in estado],
            pronostico=nuevo,
        )
        escrito = escribir_archivo(archivo, carpeta_archivo or carpeta / CARPETA_ARCHIVO)
        registro.info("Lluvia: archivo de la corrida en %s", escrito)

    producto = nuevo or anterior
    if producto is None:
        registro.error("Lluvia: sin pronóstico nuevo ni anterior; %s no se publica", RUTA_PRODUCTO)
        return None
    return entrada_manifiesto(producto)


def fuentes_lluvia_reales(catalogo: CatalogoDistritos) -> FuentesLluvia:
    return FuentesLluvia(catalogo=catalogo, proveedor=ProveedorOpenMeteo(puntos_catalogo(catalogo)))


__all__ = [
    "FuentesLluvia",
    "ProveedorEnsambles",
    "ProveedorOpenMeteo",
    "construir_producto",
    "entrada_manifiesto",
    "fuentes_lluvia_reales",
    "leer_archivo",
    "leer_producto",
    "publicar_lluvia",
]
