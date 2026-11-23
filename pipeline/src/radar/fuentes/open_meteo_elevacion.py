"""Open-Meteo Elevation API: altitud de un punto según Copernicus DEM GLO-90.

Acepta hasta 100 coordenadas por llamada y cada coordenada cuenta como una
llamada en la cuota diaria (10 000), así que se piden en grupos de 100: el
catálogo entero (unos 330 puntos) gasta unas 330 unidades de cuota y 4 peticiones.

Respuesta::

    {"elevation": [177.0, 45.0]}

o, ante un error de parámetros, ``{"error": true, "reason": "..."}``. Un punto sin
dato llega como ``NaN``; nunca se sustituye por otro valor.
"""

import json
import math
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode

import httpx

from radar.contratos.insumos_distritos import Elevaciones, Punto
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

FUENTE = "Open-Meteo Elevation API (Copernicus DEM GLO-90)"
BASE = "https://api.open-meteo.com/v1/elevation"
MAX_PUNTOS = 100
ALTITUD_MINIMA = -50.0
"""Por debajo de esto no hay tierra en el Perú: es un valor centinela de "sin dato"."""


def url_consulta(puntos: Sequence[Punto]) -> str:
    if not 1 <= len(puntos) <= MAX_PUNTOS:
        raise ValueError(f"se piden entre 1 y {MAX_PUNTOS} puntos por llamada")
    parametros = {
        "latitude": ",".join(f"{lat:.5f}" for _, lat in puntos),
        "longitude": ",".join(f"{lon:.5f}" for lon, _ in puntos),
    }
    return f"{BASE}?{urlencode(parametros, safe=',')}"


def _metros(valor: Any) -> float:
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise FuenteNoDisponible(FUENTE, f"altitud no numérica: {valor!r}")
    numero = float(valor)
    if not math.isfinite(numero) or numero < ALTITUD_MINIMA:
        raise FuenteNoDisponible(FUENTE, f"punto sin altitud válida: {valor!r}")
    return numero


class FuenteOpenMeteoElevacion:
    """Altitud de cada punto, en el orden pedido."""

    def __init__(
        self,
        puntos: Sequence[Punto],
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
    ) -> None:
        if not puntos:
            raise ValueError("no hay puntos que consultar")
        self._puntos = list(puntos)
        self._cliente = cliente
        self._politica = politica

    @property
    def id(self) -> str:
        return "open-meteo-elevacion"

    def obtener(self) -> Elevaciones:
        metros: list[float] = []
        for inicio in range(0, len(self._puntos), MAX_PUNTOS):
            grupo = self._puntos[inicio : inicio + MAX_PUNTOS]
            texto = descargar_texto(
                FUENTE, url_consulta(grupo), cliente=self._cliente, politica=self._politica
            )
            metros.extend(self.interpretar(texto, len(grupo)))
        return Elevaciones(metros=metros)

    @staticmethod
    def interpretar(texto: str, esperados: int) -> list[float]:
        """Valida una respuesta de ``esperados`` puntos. Separado para probarlo sin red."""
        try:
            datos = json.loads(texto)
        except ValueError as error:
            raise FuenteNoDisponible(FUENTE, "respuesta que no es JSON") from error
        if not isinstance(datos, dict):
            raise FuenteNoDisponible(FUENTE, "respuesta sin la lista de altitudes")
        if datos.get("error"):
            raise FuenteNoDisponible(FUENTE, f"error de la API: {datos.get('reason')}")
        valores = datos.get("elevation")
        if not isinstance(valores, list):
            raise FuenteNoDisponible(FUENTE, "respuesta sin la lista de altitudes")
        if len(valores) != esperados:
            raise FuenteNoDisponible(
                FUENTE, f"se pidieron {esperados} puntos y llegaron {len(valores)}"
            )
        return [_metros(v) for v in valores]
