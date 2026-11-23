import json
from typing import Any

import pytest

from radar.catalogo.geometria import distancia_a_lineas_km
from radar.contratos import Caja
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.natural_earth import URL, FuenteNaturalEarthCosta
from tests.ayudas import COSTA, cliente_simulado, leer_fixture, politica_sin_espera, respuesta_fija

REAL = leer_fixture(COSTA)
NORTE = Caja(lat_min=-10.0, lat_max=-3.0, lon_min=-82.0, lon_max=-76.0)
PEQUENA = Caja(lat_min=0.0, lat_max=1.0, lon_min=0.0, lon_max=1.0)


def _coleccion(*geometrias: Any) -> str:
    return json.dumps(
        {"type": "FeatureCollection", "features": [{"geometry": g} for g in geometrias]}
    )


def test_respuesta_real_da_la_distancia_al_mar() -> None:
    costa = FuenteNaturalEarthCosta(NORTE).interpretar(REAL)

    # Piura está a unos 45 km del mar; Paita, en la orilla.
    assert distancia_a_lineas_km((-80.65779, -5.1524), costa.tramos) == pytest.approx(45.7, abs=1)
    assert distancia_a_lineas_km((-81.1, -5.09), costa.tramos) < 3


def test_obtener_descarga_la_version_fijada() -> None:
    fuente = FuenteNaturalEarthCosta(
        NORTE, cliente=cliente_simulado(respuesta_fija(REAL)), politica=politica_sin_espera()
    )

    assert fuente.obtener().tramos
    assert "v5.1.2" in URL
    assert fuente.id == "natural-earth-costa"


def test_recorta_a_la_caja_con_un_vertice_de_margen() -> None:
    linea = {"type": "LineString", "coordinates": [[-1, 0.5], [0.5, 0.5], [2, 0.5], [3, 0.5]]}

    costa = FuenteNaturalEarthCosta(PEQUENA).interpretar(_coleccion(linea))

    assert costa.tramos == [[(-1.0, 0.5), (0.5, 0.5), (2.0, 0.5)]]


def test_multilinea_y_geometrias_ajenas() -> None:
    multi = {"type": "MultiLineString", "coordinates": [[[0.1, 0.1], [0.2, 0.2]], [[5, 5], [6, 6]]]}
    punto = {"type": "Point", "coordinates": [0.5, 0.5]}

    costa = FuenteNaturalEarthCosta(PEQUENA).interpretar(_coleccion(multi, punto))

    assert costa.tramos == [[(0.1, 0.1), (0.2, 0.2)]]


def test_geometrias_rotas_se_descartan() -> None:
    buena = {"type": "LineString", "coordinates": [[0.1, 0.1], [0.2, 0.2]]}
    con_nan = {"type": "LineString", "coordinates": [[0.1, float("nan")], [0.2, 0.2]]}
    sin_coordenadas = {"type": "LineString"}

    costa = FuenteNaturalEarthCosta(PEQUENA).interpretar(
        _coleccion(buena, con_nan, sin_coordenadas, None)
    )

    assert len(costa.tramos) == 1


def test_sin_costa_en_la_caja_falla() -> None:
    lejos = {"type": "LineString", "coordinates": [[50, 50], [51, 51]]}

    with pytest.raises(FuenteNoDisponible, match="ningún tramo"):
        FuenteNaturalEarthCosta(PEQUENA).interpretar(_coleccion(lejos))


@pytest.mark.parametrize("texto", ["<html></html>", "{}", "[]"])
def test_estructura_inesperada(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible, match="colección GeoJSON"):
        FuenteNaturalEarthCosta(PEQUENA).interpretar(texto)
