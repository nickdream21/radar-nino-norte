"""Natural Earth, línea de costa a escala 1:10 millones (dominio público).

Se descarga la versión 5.1.2 fijada del repositorio oficial en GitHub (GeoJSON de
unos 10 MB) y se conservan solo los tramos que tocan la caja pedida. Sirve para
medir la distancia de cada capital al mar.

Estructura::

    {"type": "FeatureCollection",
     "features": [{"geometry": {"type": "LineString", "coordinates": [[x, y], ...]}}]}
"""

import json
import logging
import math
from typing import Any

import httpx

from radar.contratos.insumos_distritos import LineaCosta, Punto
from radar.contratos.nino import Caja
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

FUENTE = "Natural Earth 1:10m, línea de costa (v5.1.2)"
URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_10m_coastline.geojson"
)


def _dentro(punto: Punto, caja: Caja) -> bool:
    lon, lat = punto
    return caja.lon_min <= lon <= caja.lon_max and caja.lat_min <= lat <= caja.lat_max


def _lineas(geometria: Any) -> list[list[Punto]]:
    tipo = geometria["type"]
    if tipo == "LineString":
        crudas = [geometria["coordinates"]]
    elif tipo == "MultiLineString":
        crudas = geometria["coordinates"]
    else:
        return []
    lineas = [[(float(p[0]), float(p[1])) for p in linea] for linea in crudas]
    if not all(math.isfinite(v) for linea in lineas for punto in linea for v in punto):
        raise ValueError("coordenada no finita")
    return lineas


def _recortar(linea: list[Punto], caja: Caja) -> list[list[Punto]]:
    """Tramos de ``linea`` con algún vértice en la caja, más un vértice a cada lado."""
    tramos: list[list[Punto]] = []
    actual: list[Punto] = []
    for i, punto in enumerate(linea):
        vecinos = linea[max(0, i - 1) : i + 2]
        if any(_dentro(p, caja) for p in vecinos):
            actual.append(punto)
        elif actual:
            tramos.append(actual)
            actual = []
    if actual:
        tramos.append(actual)
    return [t for t in tramos if len(t) >= 2]


class FuenteNaturalEarthCosta:
    """Línea de costa dentro de una caja."""

    def __init__(
        self,
        caja: Caja,
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
    ) -> None:
        self._caja = caja
        self._cliente = cliente
        self._politica = politica

    @property
    def id(self) -> str:
        return "natural-earth-costa"

    def obtener(self) -> LineaCosta:
        texto = descargar_texto(FUENTE, URL, cliente=self._cliente, politica=self._politica)
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> LineaCosta:
        """Recorta la colección GeoJSON a la caja. Separado para probarlo sin red."""
        try:
            elementos: list[Any] = json.loads(texto)["features"]
        except (ValueError, KeyError, TypeError) as error:
            raise FuenteNoDisponible(
                FUENTE, "respuesta sin la colección GeoJSON esperada"
            ) from error
        tramos: list[list[Punto]] = []
        for elemento in elementos:
            try:
                lineas = _lineas(elemento["geometry"])
            except (KeyError, TypeError, ValueError, IndexError):
                registro.warning("%s: elemento sin geometría válida descartado", FUENTE)
                continue
            for linea in lineas:
                tramos.extend(_recortar(linea, self._caja))
        if not tramos:
            raise FuenteNoDisponible(FUENTE, "ningún tramo de costa en la caja")
        return LineaCosta(tramos=tramos)
