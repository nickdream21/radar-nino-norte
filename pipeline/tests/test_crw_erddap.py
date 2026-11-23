import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.crw_erddap import CAJA_PAITA, FuenteCrwMarPaita, url_consulta
from tests.ayudas import (
    AHORA,
    CRW,
    CRW_ERROR,
    Esperas,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
    respuesta_fija,
    tiempo_agotado,
)

REAL = leer_fixture(CRW)
FECHA = "2026-11-21T12:00:00Z"


def _fuente(**opciones: object) -> FuenteCrwMarPaita:
    return FuenteCrwMarPaita(ahora=ahora_fijo, **opciones)  # type: ignore[arg-type]


def _respuesta(filas: list[list[Any]], unidades: list[str] | None = None) -> str:
    tabla: dict[str, Any] = {
        "columnNames": ["time", "latitude", "longitude", "CRW_SSTANOMALY"],
        "columnTypes": ["String", "float", "float", "double"],
        "rows": filas,
    }
    if unidades is not None:
        tabla["columnUnits"] = unidades
    return json.dumps({"table": tabla})


def test_respuesta_real() -> None:
    bloque = _fuente().interpretar(REAL)

    assert bloque.fecha_dato == datetime(2026, 11, 21, 12, tzinfo=UTC)
    assert bloque.obtenido_en == AHORA
    assert bloque.anomalia == 8.9
    assert (bloque.celdas_validas, bloque.celdas_totales) == (10, 10)
    assert bloque.caja == CAJA_PAITA


def test_url_pide_el_ultimo_dia_de_norte_a_sur() -> None:
    url = url_consulta(CAJA_PAITA)

    assert url.startswith("https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.json?")
    assert "CRW_SSTANOMALY%5B(last)%5D%5B(-5.05):1:(-5.15)%5D%5B(-81.4):1:(-81.2)%5D" in url


def test_obtener_usa_la_red_simulada() -> None:
    pedidas: list[str] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        pedidas.append(str(request.url))
        return httpx.Response(200, text=REAL, headers={"content-type": "application/json"})

    fuente = _fuente(cliente=cliente_simulado(manejador), politica=politica_sin_espera())

    assert fuente.obtener().anomalia == 8.9
    assert len(pedidas) == 1
    assert fuente.id == "crw-mar-paita"


def test_celdas_nan_relleno_y_fuera_de_rango_se_ignoran() -> None:
    texto = _respuesta(
        [
            [FECHA, -5.075, -81.375, 2.0],
            [FECHA, -5.075, -81.325, None],
            [FECHA, -5.075, -81.275, -327.68],
            [FECHA, -5.075, -81.225, 99.0],
            [FECHA, -5.075, -81.175, "x"],
            [FECHA, -5.125, -81.375, 3.0],
        ],
        ["UTC", "degrees_north", "degrees_east", "Celsius"],
    )

    bloque = _fuente().interpretar(texto)

    assert bloque.anomalia == 2.5
    assert (bloque.celdas_validas, bloque.celdas_totales) == (2, 6)


def test_nan_literal_en_el_json() -> None:
    texto = _respuesta([[FECHA, -5.075, -81.375, float("nan")], [FECHA, -5.1, -81.3, 1.5]])
    assert "NaN" in texto

    assert _fuente().interpretar(texto).anomalia == 1.5


def test_todas_las_celdas_vacias_falla() -> None:
    texto = _respuesta([[FECHA, -5.075, -81.375, None], [FECHA, -5.075, -81.325, None]])

    with pytest.raises(FuenteNoDisponible, match="ninguna celda válida"):
        _fuente().interpretar(texto)


def test_fila_incompleta_se_descarta() -> None:
    texto = _respuesta([[FECHA, -5.075, -81.375, 1.0], [FECHA, -5.075]])

    bloque = _fuente().interpretar(texto)

    assert (bloque.celdas_validas, bloque.celdas_totales) == (1, 2)


def test_fecha_sin_zona_con_columna_utc_se_acepta() -> None:
    texto = _respuesta([["2026-11-21T12:00:00", -5.1, -81.3, 1.0]], ["UTC", "", "", ""])

    assert _fuente().interpretar(texto).fecha_dato == datetime(2026, 11, 21, 12, tzinfo=UTC)


@pytest.mark.parametrize("fecha", ["2026-11-21T12:00:00", "ayer", 1795262400])
def test_fecha_sin_zona_ni_unidad_o_invalida_falla(fecha: object) -> None:
    texto = _respuesta([[fecha, -5.1, -81.3, 1.0]])

    with pytest.raises(FuenteNoDisponible, match="fecha"):
        _fuente().interpretar(texto)


def test_fecha_con_otra_zona_se_guarda_en_utc() -> None:
    texto = _respuesta([["2026-11-21T07:00:00-05:00", -5.1, -81.3, 1.0]])

    assert _fuente().interpretar(texto).fecha_dato == datetime(2026, 11, 21, 12, tzinfo=UTC)


def test_varios_dias_falla() -> None:
    texto = _respuesta([[FECHA, -5.1, -81.3, 1.0], ["2026-11-20T12:00:00Z", -5.1, -81.3, 1.0]])

    with pytest.raises(FuenteNoDisponible, match="un solo día"):
        _fuente().interpretar(texto)


@pytest.mark.parametrize(
    "texto",
    [
        '{"table": {"columnNames": ["time", "latitude", "longitude", "OTRA"], "rows": []}}',
        '{"datos": []}',
        "no es json",
        "[]",
    ],
)
def test_estructura_inesperada(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible, match="tabla esperada"):
        _fuente().interpretar(texto)


def test_tabla_vacia() -> None:
    with pytest.raises(FuenteNoDisponible, match="no tiene filas"):
        _fuente().interpretar(_respuesta([]))


def test_error_de_erddap_se_reintenta_y_falla() -> None:
    esperas = Esperas()
    error = respuesta_fija(leer_fixture(CRW_ERROR), estado=500)
    fuente = _fuente(cliente=cliente_simulado(error), politica=politica_sin_espera(esperas))

    with pytest.raises(FuenteNoDisponible, match="HTTP 500 tras 3 intentos"):
        fuente.obtener()
    assert len(esperas) == 2


def test_respuesta_html() -> None:
    html = respuesta_fija("<html><head><title>ERDDAP</title></head></html>", tipo="text/html")
    fuente = _fuente(cliente=cliente_simulado(html), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()


def test_tiempo_de_espera_agotado() -> None:
    fuente = _fuente(cliente=cliente_simulado(tiempo_agotado), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="tiempo de espera"):
        fuente.obtener()
