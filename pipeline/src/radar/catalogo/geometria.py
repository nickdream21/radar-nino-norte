"""Geometría mínima sobre puntos (longitud, latitud): distancias y punto en polígono.

Basta una proyección equirectangular local alrededor de cada punto: las distancias
que importan aquí son de decenas de kilómetros y el error es muy inferior a los
márgenes de duda de la regla de zonas. Así se evita una dependencia geoespacial.
"""

import math
from collections.abc import Iterable, Sequence
from itertools import pairwise

from radar.contratos.insumos_distritos import Punto

RADIO_TIERRA_KM = 6371.0088


def distancia_km(a: Punto, b: Punto) -> float:
    """Distancia de círculo máximo (haversine)."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))


def _a_km(origen: Punto, punto: Punto) -> tuple[float, float]:
    """Coordenadas planas en km de ``punto`` respecto a ``origen``."""
    km_por_grado = math.pi * RADIO_TIERRA_KM / 180
    x = (punto[0] - origen[0]) * km_por_grado * math.cos(math.radians(origen[1]))
    y = (punto[1] - origen[1]) * km_por_grado
    return x, y


def _distancia_a_segmento(ax: float, ay: float, bx: float, by: float) -> float:
    """Distancia del origen al segmento AB, en el plano."""
    dx, dy = bx - ax, by - ay
    largo2 = dx * dx + dy * dy
    t = 0.0 if largo2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / largo2))
    return math.hypot(ax + t * dx, ay + t * dy)


def distancia_a_lineas_km(punto: Punto, lineas: Iterable[Sequence[Punto]]) -> float:
    """Distancia mínima de ``punto`` a un conjunto de polilíneas (o anillos)."""
    mejor = math.inf
    for linea in lineas:
        planos = [_a_km(punto, p) for p in linea]
        for (ax, ay), (bx, by) in pairwise(planos):
            # Descarte rápido: el segmento entero está más lejos que lo ya encontrado.
            if min(abs(ax), abs(bx)) > mejor and (ax > 0) == (bx > 0):
                continue
            if min(abs(ay), abs(by)) > mejor and (ay > 0) == (by > 0):
                continue
            mejor = min(mejor, _distancia_a_segmento(ax, ay, bx, by))
    return mejor


def dentro(punto: Punto, anillos: Iterable[Sequence[Punto]]) -> bool:
    """Regla par-impar: dentro si un rayo hacia el este cruza un número impar de bordes."""
    x, y = punto
    cruces = 0
    for anillo in anillos:
        n = len(anillo)
        for i in range(n):
            x1, y1 = anillo[i]
            x2, y2 = anillo[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                cruces += 1
    return cruces % 2 == 1
