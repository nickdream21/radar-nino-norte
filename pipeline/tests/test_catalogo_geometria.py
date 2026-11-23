import math

import pytest

from radar.catalogo.geometria import dentro, distancia_a_lineas_km, distancia_km

CUADRADO = [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]]
HUECO = [(0.4, 0.4), (0.6, 0.4), (0.6, 0.6), (0.4, 0.6), (0.4, 0.4)]


def test_distancia_entre_piura_y_chiclayo() -> None:
    # Unos 200 km en línea recta.
    assert distancia_km((-80.6578, -5.1524), (-79.8409, -6.7714)) == pytest.approx(200, abs=5)


def test_un_grado_de_meridiano() -> None:
    assert distancia_km((0.0, 0.0), (0.0, 1.0)) == pytest.approx(111.19, abs=0.01)


def test_distancia_a_una_linea() -> None:
    linea = [(0.0, 0.0), (0.0, 2.0)]

    assert distancia_a_lineas_km((0.1, 1.0), [linea]) == pytest.approx(11.12, abs=0.05)
    # Más allá del extremo, la distancia es al vértice.
    assert distancia_a_lineas_km((0.0, 3.0), [linea]) == pytest.approx(111.19, abs=0.1)


def test_distancia_a_la_mas_cercana_de_varias_lineas() -> None:
    lejana = [(5.0, 5.0), (6.0, 5.0)]
    cercana = [(0.0, 0.01), (1.0, 0.01)]

    assert distancia_a_lineas_km((0.5, 0.0), [lejana, cercana]) == pytest.approx(1.11, abs=0.01)


def test_sin_lineas_la_distancia_es_infinita() -> None:
    assert distancia_a_lineas_km((0.0, 0.0), []) == math.inf


def test_segmento_degenerado() -> None:
    assert distancia_a_lineas_km((0.0, 0.0), [[(0.0, 1.0), (0.0, 1.0)]]) == pytest.approx(
        111.19, abs=0.1
    )


def test_punto_en_poligono_con_hueco() -> None:
    assert dentro((0.2, 0.2), CUADRADO)
    assert not dentro((1.5, 0.5), CUADRADO)
    assert not dentro((0.5, 0.5), [*CUADRADO, HUECO])
    assert dentro((0.3, 0.5), [*CUADRADO, HUECO])
