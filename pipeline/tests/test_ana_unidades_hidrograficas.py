import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from radar.catalogo.geometria import dentro
from radar.contratos import Caja
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.ana_unidades_hidrograficas import (
    MAX_PAGINAS,
    FuenteAnaUnidadesHidrograficas,
    url_pagina,
)
from tests.ayudas import ANA, ANA_ERROR, cliente_simulado, leer_fixture, politica_sin_espera

REAL = leer_fixture(ANA)
CAJA = Caja(lat_min=-5.65, lat_max=-5.45, lon_min=-79.6, lon_max=-79.4)
HUARMACA = (-79.52452, -5.56797)
"""Capital de Huarmaca según el INEI."""


def _fuente(**opciones: object) -> FuenteAnaUnidadesHidrograficas:
    return FuenteAnaUnidadesHidrograficas(CAJA, **opciones)  # type: ignore[arg-type]


def _elemento(codigo: str = "1378", nivel1: str = "1", anillos: Any = None) -> dict[str, Any]:
    return {
        "attributes": {"codigo": codigo, "nombre": f"Unidad {codigo}", "nivel1": nivel1},
        "geometry": {"rings": anillos or [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    }


def _pagina(*elementos: dict[str, Any], mas: bool = False) -> str:
    return json.dumps({"features": list(elementos), "exceededTransferLimit": mas})


def test_respuesta_real_distingue_las_vertientes() -> None:
    lista = _fuente().interpretar([REAL])

    por_codigo = {u.codigo: u for u in lista.unidades}
    assert set(por_codigo) == {"1378", "49896"}
    assert por_codigo["1378"].nombre == "Cuenca Piura"
    assert por_codigo["1378"].vertiente == "pacifico"
    assert por_codigo["49896"].nombre == "Cuenca Chamaya"
    assert por_codigo["49896"].vertiente == "atlantico"
    # La capital de Huarmaca cae en la cuenca del Piura, junto a la divisoria.
    assert dentro(HUARMACA, por_codigo["1378"].anillos)
    assert not dentro(HUARMACA, por_codigo["49896"].anillos)


def test_url_pide_la_caja_con_contorno_simplificado() -> None:
    consulta = parse_qs(urlparse(url_pagina(CAJA, 200)).query)

    assert consulta["geometry"] == ["-79.6,-5.65,-79.4,-5.45"]
    assert consulta["outSR"] == ["4326"]
    assert consulta["resultOffset"] == ["200"]
    assert consulta["maxAllowableOffset"] == ["0.001"]


def test_obtener_recorre_las_paginas() -> None:
    paginas = iter([_pagina(_elemento("1378"), mas=True), _pagina(_elemento("49896", nivel1="4"))])
    pedidas: list[str] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        pedidas.append(parse_qs(request.url.query.decode())["resultOffset"][0])
        return httpx.Response(200, text=next(paginas), headers={"content-type": "application/json"})

    fuente = _fuente(cliente=cliente_simulado(manejador), politica=politica_sin_espera())
    lista = fuente.obtener()

    assert [u.codigo for u in lista.unidades] == ["1378", "49896"]
    assert pedidas == ["0", "100"]
    assert fuente.id == "ana-unidades-hidrograficas"


def test_demasiadas_paginas_falla() -> None:
    contador = iter(range(1000))

    def sin_fin(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_pagina(_elemento(str(next(contador))), mas=True))

    fuente = _fuente(cliente=cliente_simulado(sin_fin), politica=politica_sin_espera())
    with pytest.raises(FuenteNoDisponible, match=f"más de {MAX_PAGINAS} páginas"):
        fuente.obtener()


def test_error_del_servicio_con_estado_200() -> None:
    with pytest.raises(FuenteNoDisponible, match="error del servicio"):
        _fuente().interpretar([leer_fixture(ANA_ERROR)])


def test_region_hidrografica_desconocida_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="región hidrográfica desconocida"):
        _fuente().interpretar([_pagina(_elemento(nivel1="0"))])


def test_unidades_rotas_se_descartan() -> None:
    sin_geometria = _elemento("2") | {"geometry": None}
    anillo_corto = _elemento("3", anillos=[[[0, 0], [1, 1]]])
    con_nan = _elemento("4", anillos=[[[0, 0], [float("nan"), 0], [1, 1], [0, 0]]])

    lista = _fuente().interpretar([_pagina(_elemento("1"), sin_geometria, anillo_corto, con_nan)])

    assert [u.codigo for u in lista.unidades] == ["1"]


def test_ninguna_unidad_valida_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="ninguna unidad"):
        _fuente().interpretar([_pagina()])


def test_unidades_repetidas_entre_paginas_fallan() -> None:
    with pytest.raises(FuenteNoDisponible, match="repetidas"):
        _fuente().interpretar([_pagina(_elemento("1")), _pagina(_elemento("1"))])


@pytest.mark.parametrize("texto", ["no es json", "[]", '{"otra": 1}'])
def test_estructura_inesperada(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible):
        _fuente().interpretar([texto])


def test_html_en_lugar_de_datos() -> None:
    def html(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>Error</html>", headers={"content-type": "text/html"})

    fuente = _fuente(cliente=cliente_simulado(html), politica=politica_sin_espera())
    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()
