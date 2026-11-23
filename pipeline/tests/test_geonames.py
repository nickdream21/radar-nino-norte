import io
import zipfile

import httpx
import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.geonames import FuenteGeonames
from tests.ayudas import GEONAMES, cliente_simulado, leer_fixture, politica_sin_espera

REAL = leer_fixture(GEONAMES)
DEPARTAMENTOS = ("06", "13", "14", "20", "24")
LINEA = (
    "3694256\tOlmos\tOlmos\t\t-5.98451\t-79.74678\tP\tPPLA3\tPE\t\t14\t1403\t140308\t\t0\t"
    "{elevacion}\t{dem}\tAmerica/Lima\t2017-01-23"
)


def _zip(texto: str, nombre: str = "PE.txt") -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as archivo:
        archivo.writestr(nombre, texto.encode("utf-8"))
    return memoria.getvalue()


def test_respuesta_real() -> None:
    lugares = FuenteGeonames(DEPARTAMENTOS).interpretar(REAL).lugares

    por_id = {lugar.geonameid: lugar for lugar in lugares}
    olmos = por_id["3694256"]
    assert (olmos.nombre, olmos.clase, olmos.ubigeo) == ("Olmos", "PPLA3", "140308")
    assert (olmos.altitud_m, olmos.altitud_mde_m) == (None, 175)
    assert por_id["8350639"].ubigeo == "200114"  # ADM3 Tambo Grande
    assert por_id["3693524"].ubigeo == "2001"  # ADM2 Piura
    assert por_id["3693525"].ubigeo == "20"  # ADM1 Piura
    assert por_id["3699088"].altitud_m == 2700
    # Alto Trujillo aún figura en el distrito de El Porvenir.
    assert por_id["13562177"].ubigeo == "130102"
    # Fuera de los cinco departamentos (Amazonas) no se conserva.
    assert all(not lugar.ubigeo.startswith("01") for lugar in lugares)


def test_dem_sin_dato_y_elevacion_vacia() -> None:
    lugares = FuenteGeonames(["14"]).interpretar(LINEA.format(elevacion="", dem="-9999")).lugares

    assert (lugares[0].altitud_m, lugares[0].altitud_mde_m) == (None, None)


def test_lineas_incompletas_o_invalidas_se_descartan() -> None:
    buena = LINEA.format(elevacion="", dem="175")
    corta = "3694256\tOlmos\tOlmos"
    sin_coordenada = buena.replace("-5.98451", "")
    con_nan = buena.replace("-5.98451", "nan")
    otra_clase = buena.replace("\tP\tPPLA3\t", "\tH\tSTM\t")

    lugares = (
        FuenteGeonames(["14"])
        .interpretar("\n".join([buena, corta, sin_coordenada, con_nan, otra_clase, ""]))
        .lugares
    )

    assert len(lugares) == 1


def test_ningun_lugar_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="ningún lugar"):
        FuenteGeonames(["24"]).interpretar(LINEA.format(elevacion="", dem="1"))


def test_obtener_lee_el_zip() -> None:
    contenido = _zip(REAL)

    def manejador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=contenido, headers={"content-type": "application/zip"})

    fuente = FuenteGeonames(
        DEPARTAMENTOS, cliente=cliente_simulado(manejador), politica=politica_sin_espera()
    )

    assert len(fuente.obtener().lugares) > 50
    assert fuente.id == "geonames"


@pytest.mark.parametrize("contenido", [_zip("x", nombre="otro.txt"), b"no es un zip"])
def test_zip_sin_pe_txt(contenido: bytes) -> None:
    def manejador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=contenido)

    fuente = FuenteGeonames(
        DEPARTAMENTOS, cliente=cliente_simulado(manejador), politica=politica_sin_espera()
    )
    with pytest.raises(FuenteNoDisponible, match=r"PE\.txt"):
        fuente.obtener()
