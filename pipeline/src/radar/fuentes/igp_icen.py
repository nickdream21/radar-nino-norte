"""IGP: Índice Costero El Niño (ICEN) mensual del ENFEN.

Texto plano, solo por HTTP y con nombre sensible a mayúsculas (``ICEN.txt``). Las
líneas de cabecera empiezan con ``%`` y la última nombra las columnas::

    % yy   mm   ICEN
    2026   9    4.50

El ICEN es una media móvil de tres meses centrada en ``mm``, por eso el último
valor publicado va unos dos meses por detrás del mes en curso.
"""

import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from radar.contratos import BloqueIcen, ValorMensual
from radar.contratos.nino import MAX_MESES
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

URL = "http://met.igp.gob.pe/datos/ICEN.txt"
FUENTE = "IGP (ICEN, ENFEN)"
COLUMNAS = ("yy", "mm", "ICEN")


def leer_tabla(texto: str) -> list[ValorMensual]:
    """Convierte el archivo en la serie mensual, sin rellenar huecos.

    Exige la cabecera de columnas esperada. Las filas incompletas, con texto
    o con centinelas (-99.99, NaN) se descartan y se registran.
    """
    lineas = texto.splitlines()
    cabeceras = [tuple(linea.lstrip("%").split()) for linea in lineas if linea.startswith("%")]
    if COLUMNAS not in cabeceras:
        raise FuenteNoDisponible(FUENTE, "cabecera de columnas inesperada")
    serie: list[ValorMensual] = []
    for numero, linea in enumerate(lineas, start=1):
        if linea.startswith("%") or not linea.strip():
            continue
        partes = linea.split()
        try:
            if len(partes) != len(COLUMNAS):
                raise ValueError("número de columnas distinto de 3")
            anio, mes, valor = int(partes[0]), int(partes[1]), float(partes[2])
            if not math.isfinite(valor) or valor <= -99:
                raise ValueError("valor centinela")
            mensual = ValorMensual(
                anio=anio, mes=mes, fecha=datetime(anio, mes, 1, tzinfo=UTC), valor=valor
            )
        except (ValueError, ValidationError) as error:
            registro.warning("%s: línea %d descartada (%s)", FUENTE, numero, error)
            continue
        if serie and mensual.fecha <= serie[-1].fecha:
            raise FuenteNoDisponible(FUENTE, f"meses desordenados o repetidos en la línea {numero}")
        serie.append(mensual)
    if not serie:
        raise FuenteNoDisponible(FUENTE, "sin ningún valor válido")
    return serie


class FuenteIgpIcen:
    """ICEN mensual publicado por el IGP."""

    def __init__(
        self,
        *,
        meses: int = MAX_MESES,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not 1 <= meses <= MAX_MESES:
            raise ValueError(f"meses debe estar entre 1 y {MAX_MESES}")
        self._meses = meses
        self._cliente = cliente
        self._politica = politica
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "igp-icen"

    def obtener(self) -> BloqueIcen:
        texto = descargar_texto(FUENTE, URL, cliente=self._cliente, politica=self._politica)
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> BloqueIcen:
        """Convierte la respuesta en el bloque publicado. Separado para probarlo sin red."""
        serie = leer_tabla(texto)[-self._meses :]
        if len(serie) < self._meses:
            registro.warning("%s: solo hay %d meses válidos", FUENTE, len(serie))
        return BloqueIcen(
            fuente=FUENTE,
            url=URL,
            fecha_dato=serie[-1].fecha,
            obtenido_en=self._ahora(),
            ultimo=serie[-1],
            serie=serie,
        )
