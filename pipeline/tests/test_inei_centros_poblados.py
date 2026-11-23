import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.inei_centros_poblados import FuenteIneiCapitales, url_capitales
from tests.ayudas import (
    INEI_CAPITALES,
    INEI_EXCEPCION,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
    respuesta_fija,
)

REAL = leer_fixture(INEI_CAPITALES)
MUESTRA = ["060101", "060801", "130101", "130809", "140308", "200101", "200114", "240101"]


def _elemento(**propiedades: Any) -> dict[str, Any]:
    base = {"ubigeo": "240101", "codccpp": "0001", "nombccpp": "TUMBES"}
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-80.45, -3.57]},
        "properties": base | propiedades,
    }


def _coleccion(*elementos: dict[str, Any], coincidentes: int | None = None) -> str:
    datos: dict[str, Any] = {"type": "FeatureCollection", "features": list(elementos)}
    if coincidentes is not None:
        datos["numberMatched"] = coincidentes
    return json.dumps(datos)


def test_respuesta_real() -> None:
    lista = FuenteIneiCapitales(MUESTRA).interpretar(REAL)

    assert [c.ubigeo for c in lista.centros] == MUESTRA
    olmos = next(c for c in lista.centros if c.ubigeo == "140308")
    assert (olmos.nombre, olmos.codigo) == ("OLMOS", "0001")
    assert olmos.latitud == pytest.approx(-5.9879, abs=1e-3)
    assert olmos.longitud == pytest.approx(-79.7475, abs=1e-3)


def test_url_filtra_capitales_de_los_distritos_pedidos() -> None:
    consulta = parse_qs(urlparse(url_capitales(["240102", "240101", "240101"])).query)

    assert consulta["typeName"] == ["Interoperabilidad:ig_centropoblado"]
    assert consulta["CQL_FILTER"] == ["codccpp='0001' AND ubigeo IN ('240101','240102')"]
    assert consulta["outputFormat"] == ["application/json"]


@pytest.mark.parametrize("ubigeos", [[], ["2401"], ["24010a"]])
def test_url_rechaza_ubigeos_invalidos(ubigeos: list[str]) -> None:
    with pytest.raises(ValueError, match="6 dígitos"):
        url_capitales(ubigeos)


def test_obtener_usa_la_red_simulada() -> None:
    fuente = FuenteIneiCapitales(
        MUESTRA,
        cliente=cliente_simulado(respuesta_fija(REAL, tipo="application/json")),
        politica=politica_sin_espera(),
    )

    assert len(fuente.obtener().centros) == len(MUESTRA)
    assert fuente.id == "inei-capitales"


def test_elementos_sin_geometria_o_incompletos_se_descartan() -> None:
    sin_punto = _elemento(ubigeo="240102") | {"geometry": None}
    sin_nombre = _elemento(ubigeo="240103", nombccpp=None)
    coordenada_nan = _elemento(ubigeo="240104") | {
        "geometry": {"type": "Point", "coordinates": [float("nan"), -3.5]}
    }
    sin_propiedades = {"type": "Feature", "geometry": None}

    lista = FuenteIneiCapitales(["240101"]).interpretar(
        _coleccion(_elemento(), sin_punto, sin_nombre, coordenada_nan, sin_propiedades)
    )

    assert [c.ubigeo for c in lista.centros] == ["240101"]


def test_respuesta_truncada_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="truncada"):
        FuenteIneiCapitales(["240101"]).interpretar(_coleccion(_elemento(), coincidentes=5))


def test_dos_capitales_para_un_distrito_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="dos capitales"):
        FuenteIneiCapitales(["240101"]).interpretar(_coleccion(_elemento(), _elemento()))


def test_centro_poblado_que_no_es_capital_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="0002"):
        FuenteIneiCapitales(["240101"]).interpretar(_coleccion(_elemento(codccpp="0002")))


@pytest.mark.parametrize(
    "texto", ["no es json", '{"type": "FeatureCollection"}', '{"features": {}}']
)
def test_estructura_inesperada(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible, match="colección GeoJSON"):
        FuenteIneiCapitales(["240101"]).interpretar(texto)


def test_excepcion_xml_del_geoservidor() -> None:
    # Un filtro mal formado devuelve un informe de excepción XML con estado 200.
    excepcion = respuesta_fija(leer_fixture(INEI_EXCEPCION), tipo="text/xml;charset=UTF-8")
    fuente = FuenteIneiCapitales(
        ["240101"], cliente=cliente_simulado(excepcion), politica=politica_sin_espera()
    )

    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()


def test_servidor_caido() -> None:
    def caido(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    fuente = FuenteIneiCapitales(
        ["240101"], cliente=cliente_simulado(caido), politica=politica_sin_espera(intentos=2)
    )

    with pytest.raises(FuenteNoDisponible, match="HTTP 503 tras 2 intentos"):
        fuente.obtener()
