"""NOAA CPC: índices semanales de temperatura del mar en las regiones Niño.

Archivo de texto de ancho fijo (``wksst9120.for``), una fila por semana desde 1981::

                    Nino1+2      Nino3        Nino34        Nino4
     Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA
     11NOV2026     27.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3

Cada región ocupa 13 columnas: 5 espacios, la temperatura en 4 y la anomalía en 4.
Las anomalías negativas quedan pegadas a la temperatura (``20.6-0.1``), por eso no
se separa por espacios: se extraen los números por su forma, lo que también aguanta
un centinela más ancho que la columna (``-99.9``). La fecha es el día central de la semana.
"""

import logging
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from radar.contratos import BloqueIndicesSemanales, IndiceSemanal, ValorSemanal
from radar.contratos.nino import MAX_SEMANAS
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
FUENTE = "NOAA CPC"
REGIONES = ("Nino1+2", "Nino3", "Nino34", "Nino4")
"""Orden de las regiones en el archivo; se comprueba contra la cabecera."""

_ANCHO_FECHA = 10
_NUMERO = re.compile(r"-?(?:\d+(?:\.\d+)?|nan)", re.IGNORECASE)
_MESES = {
    m: i
    for i, m in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"),
        start=1,
    )
}


def _fecha(texto: str) -> datetime:
    """``02SEP1981`` → 1981-09-02 00:00 UTC, sin depender del idioma del sistema."""
    dia, mes, anio = texto[:2], texto[2:5], texto[5:]
    if mes not in _MESES or not (dia.isdigit() and anio.isdigit() and len(anio) == 4):
        raise ValueError(f"fecha no reconocida: {texto!r}")
    return datetime(int(anio), _MESES[mes], int(dia), tzinfo=UTC)


def _numero(texto: str) -> float | None:
    """Número de la tabla, o ``None`` si es un centinela (-99.9, NaN) o está vacío."""
    try:
        valor = float(texto)
    except ValueError:
        return None
    if not math.isfinite(valor) or valor <= -99:
        return None
    return valor


def _comprobar_cabecera(lineas: list[str]) -> int:
    """Devuelve el índice de la línea ``Week``; falla si las regiones no son las esperadas."""
    for i, linea in enumerate(lineas):
        if linea.split()[:1] == ["Week"]:
            if i == 0 or tuple(lineas[i - 1].split()) != REGIONES:
                raise FuenteNoDisponible(FUENTE, "cabecera de regiones inesperada")
            if linea.split() != ["Week", *["SST", "SSTA"] * len(REGIONES)]:
                raise FuenteNoDisponible(FUENTE, "cabecera de columnas inesperada")
            return i
    raise FuenteNoDisponible(FUENTE, "no se encontró la cabecera de la tabla")


def leer_tabla(texto: str) -> dict[str, list[ValorSemanal]]:
    """Convierte el archivo en una serie por región, sin rellenar huecos.

    Las filas incompletas y los valores centinela se descartan (solo en la región
    afectada) y se registran. Las fechas deben ir en orden estrictamente creciente.
    """
    lineas = texto.splitlines()
    inicio = _comprobar_cabecera(lineas)
    series: dict[str, list[ValorSemanal]] = {r: [] for r in REGIONES}
    descartadas = 0
    anterior: datetime | None = None
    for numero, linea in enumerate(lineas[inicio + 1 :], start=inicio + 2):
        if not linea.strip():
            continue
        try:
            fecha = _fecha(linea[:_ANCHO_FECHA].strip())
        except ValueError:
            registro.warning("%s: línea %d sin fecha válida, se descarta", FUENTE, numero)
            descartadas += 1
            continue
        numeros = _NUMERO.findall(linea[_ANCHO_FECHA:])
        if len(numeros) != 2 * len(REGIONES):
            registro.warning("%s: línea %d incompleta, se descarta", FUENTE, numero)
            descartadas += 1
            continue
        if anterior is not None and fecha <= anterior:
            raise FuenteNoDisponible(
                FUENTE, f"fechas desordenadas o repetidas en la línea {numero}"
            )
        anterior = fecha
        for k, region in enumerate(REGIONES):
            temperatura = _numero(numeros[2 * k])
            anomalia = _numero(numeros[2 * k + 1])
            if temperatura is None or anomalia is None:
                registro.warning("%s: %s sin dato en la línea %d", FUENTE, region, numero)
                continue
            try:
                valor = ValorSemanal(fecha=fecha, temperatura=temperatura, anomalia=anomalia)
            except ValidationError:
                registro.warning("%s: %s fuera de rango en la línea %d", FUENTE, region, numero)
                continue
            series[region].append(valor)
    if descartadas:
        registro.warning("%s: %d líneas descartadas", FUENTE, descartadas)
    return series


def _indice(serie: list[ValorSemanal], semanas: int, region: str) -> IndiceSemanal:
    if not serie:
        raise FuenteNoDisponible(FUENTE, f"{region} sin ningún valor válido")
    recorte = serie[-semanas:]
    if len(recorte) < semanas:
        registro.warning("%s: %s solo tiene %d semanas válidas", FUENTE, region, len(recorte))
    return IndiceSemanal(ultimo=recorte[-1], serie=recorte)


class FuenteNoaaCpcSemanal:
    """Niño 1+2 y Niño 3.4 semanales del CPC de NOAA."""

    def __init__(
        self,
        *,
        semanas: int = MAX_SEMANAS,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not 1 <= semanas <= MAX_SEMANAS:
            raise ValueError(f"semanas debe estar entre 1 y {MAX_SEMANAS}")
        self._semanas = semanas
        self._cliente = cliente
        self._politica = politica
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "noaa-cpc-semanal"

    def obtener(self) -> BloqueIndicesSemanales:
        texto = descargar_texto(FUENTE, URL, cliente=self._cliente, politica=self._politica)
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> BloqueIndicesSemanales:
        """Convierte la respuesta en el bloque publicado. Separado para probarlo sin red."""
        series = leer_tabla(texto)
        nino12 = _indice(series["Nino1+2"], self._semanas, "Niño 1+2")
        nino34 = _indice(series["Nino34"], self._semanas, "Niño 3.4")
        return BloqueIndicesSemanales(
            fuente=FUENTE,
            url=URL,
            fecha_dato=max(nino12.ultimo.fecha, nino34.ultimo.fecha),
            obtenido_en=self._ahora(),
            nino12=nino12,
            nino34=nino34,
        )
