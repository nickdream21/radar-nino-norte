"""NOAA Coral Reef Watch 5 km (``dhw_5km``) por el ERDDAP de PacIOOS.

Se pide la anomalía diaria de temperatura del mar (``CRW_SSTANOMALY``) del último
día disponible en una caja pequeña mar adentro y se promedian las celdas válidas.
Las celdas pegadas a la costa vienen como ``null`` (tierra o máscara); se ignoran,
nunca se rellenan. El producto va unos dos días por detrás.

Respuesta ``.json`` de ERDDAP::

    {"table": {"columnNames": ["time", "latitude", "longitude", "CRW_SSTANOMALY"],
               "columnUnits": ["UTC", "degrees_north", "degrees_east", "Celsius"],
               "rows": [["2026-11-21T12:00:00Z", -5.075, -81.375, 8.95], ...]}}
"""

import json
import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from radar.contratos import BloqueMarPaita, Caja
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

BASE = "https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km"
FUENTE = "NOAA Coral Reef Watch 5 km (ERDDAP PacIOOS)"
VARIABLE = "CRW_SSTANOMALY"
VALOR_RELLENO = -327.68
"""``_FillValue`` declarado por el conjunto de datos."""
RANGO_VALIDO = (-15.0, 15.0)
"""``valid_min`` y ``valid_max`` declarados por el conjunto de datos."""

CAJA_PAITA = Caja(lat_min=-5.15, lat_max=-5.05, lon_min=-81.4, lon_max=-81.2)
"""Mar adentro frente a Paita: 2 por 5 celdas de 0.05°, fuera de la franja costera sin datos."""


def url_consulta(caja: Caja) -> str:
    """URL griddap del último día en ``caja``. La latitud del conjunto va de norte a sur."""
    return (
        f"{BASE}.json?{VARIABLE}"
        f"%5B(last)%5D"
        f"%5B({caja.lat_max}):1:({caja.lat_min})%5D"
        f"%5B({caja.lon_min}):1:({caja.lon_max})%5D"
    )


def _fecha(texto: Any, unidad: Any) -> datetime:
    if not isinstance(texto, str):
        raise FuenteNoDisponible(FUENTE, f"fecha no reconocida: {texto!r}")
    try:
        fecha = datetime.fromisoformat(texto)
    except ValueError as error:
        raise FuenteNoDisponible(FUENTE, f"fecha no reconocida: {texto!r}") from error
    if fecha.tzinfo is None:
        # ERDDAP siempre escribe la "Z"; sin ella solo se acepta si la columna se declara UTC.
        if unidad != "UTC":
            raise FuenteNoDisponible(FUENTE, f"fecha sin zona horaria: {texto!r}")
        fecha = fecha.replace(tzinfo=UTC)
    return fecha.astimezone(UTC)


def _valido(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return None
    numero = float(valor)
    if not math.isfinite(numero) or math.isclose(numero, VALOR_RELLENO):
        return None
    if not RANGO_VALIDO[0] <= numero <= RANGO_VALIDO[1]:
        return None
    return numero


class FuenteCrwMarPaita:
    """Anomalía diaria del mar frente a Paita."""

    def __init__(
        self,
        *,
        caja: Caja = CAJA_PAITA,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._caja = caja
        self._cliente = cliente
        self._politica = politica
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "crw-mar-paita"

    def obtener(self) -> BloqueMarPaita:
        texto = descargar_texto(
            FUENTE, url_consulta(self._caja), cliente=self._cliente, politica=self._politica
        )
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> BloqueMarPaita:
        """Convierte la respuesta en el bloque publicado. Separado para probarlo sin red."""
        try:
            tabla = json.loads(texto)["table"]
            columnas: list[str] = tabla["columnNames"]
            unidades: list[str] = tabla.get("columnUnits") or [""] * len(columnas)
            filas: list[list[Any]] = tabla["rows"]
            i_tiempo, i_valor = columnas.index("time"), columnas.index(VARIABLE)
        except (ValueError, KeyError, TypeError) as error:
            raise FuenteNoDisponible(FUENTE, "respuesta sin la tabla esperada") from error
        if not filas:
            raise FuenteNoDisponible(FUENTE, "la tabla no tiene filas")

        fechas: set[datetime] = set()
        validos: list[float] = []
        for fila in filas:
            if not isinstance(fila, list) or len(fila) != len(columnas):
                registro.warning("%s: fila incompleta descartada: %r", FUENTE, fila)
                continue
            fechas.add(_fecha(fila[i_tiempo], unidades[i_tiempo]))
            valor = _valido(fila[i_valor])
            if valor is not None:
                validos.append(valor)
        if len(fechas) != 1:
            raise FuenteNoDisponible(FUENTE, f"se esperaba un solo día y llegaron {len(fechas)}")
        if not validos:
            raise FuenteNoDisponible(FUENTE, "ninguna celda válida en la caja")
        if len(validos) < len(filas):
            registro.info("%s: %d de %d celdas válidas", FUENTE, len(validos), len(filas))
        fecha = fechas.pop()
        return BloqueMarPaita(
            fuente=FUENTE,
            url=BASE,
            fecha_dato=fecha,
            obtenido_en=self._ahora(),
            anomalia=round(sum(validos) / len(validos), 2),
            caja=self._caja,
            celdas_validas=len(validos),
            celdas_totales=len(filas),
        )
