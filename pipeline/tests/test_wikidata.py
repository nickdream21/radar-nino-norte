import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from radar.cli import DATOS_ESTATICOS
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.wikidata import (
    URL,
    FuenteWikidataArchivo,
    FuenteWikidataNombres,
    consulta,
    interpretar_instantanea,
)
from tests.ayudas import WIKIDATA, ahora_fijo, cliente_simulado, leer_fixture, politica_sin_espera

REAL = leer_fixture(WIKIDATA)


def _fila(gn: str, etiqueta: str) -> dict[str, object]:
    return {"gn": {"value": gn}, "l": {"xml:lang": "es", "value": etiqueta}}


def _instantanea(*filas: object, fecha: str = "2026-11-23T15:19:27Z") -> str:
    return json.dumps({"descargado_en": fecha, "respuesta": {"results": {"bindings": list(filas)}}})


def test_instantanea_real() -> None:
    nombres = interpretar_instantanea(REAL)

    assert nombres.descargado_en == datetime(2026, 11, 23, 15, 19, 27, tzinfo=UTC)
    assert nombres.por_geonameid["8349822"] == "Jaén"
    assert nombres.por_geonameid["8349657"] == "Distrito de El Tallán"


def test_instantanea_del_repositorio_es_valida() -> None:
    nombres = FuenteWikidataArchivo(
        DATOS_ESTATICOS / "fuentes" / "wikidata-etiquetas.json"
    ).obtener()

    assert len(nombres.por_geonameid) > 600


def test_etiquetas_ambiguas_o_incompletas_se_descartan() -> None:
    nombres = interpretar_instantanea(
        _instantanea(
            _fila("1", "Jaén"),
            _fila("2", "Uno"),
            _fila("2", "Otro"),
            {"gn": {"value": "3"}},
            _fila("x", "No numérico"),
            _fila("4", ""),
        )
    )

    assert nombres.por_geonameid == {"1": "Jaén"}


@pytest.mark.parametrize(
    "texto",
    [
        "no es json",
        '{"respuesta": {"results": {"bindings": []}}}',
        _instantanea(fecha="2026-11-23T15:19:27"),
        json.dumps({"descargado_en": "2026-11-23T15:19:27Z", "respuesta": {"results": {}}}),
    ],
)
def test_instantanea_invalida(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible):
        interpretar_instantanea(texto)


def test_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(FuenteNoDisponible, match="no se pudo leer"):
        FuenteWikidataArchivo(tmp_path / "no-existe.json").obtener()


def test_consulta_enlaza_por_geonames() -> None:
    texto = consulta(["3", "1", "1"])

    assert 'VALUES ?gn { "1" "3" }' in texto
    assert "wdt:P1566" in texto
    with pytest.raises(ValueError, match="numéricos"):
        consulta(["Q1"])


def test_en_linea_exige_contacto() -> None:
    with pytest.raises(ValueError, match="contacto"):
        FuenteWikidataNombres(["1"], contacto=" ")


def test_en_linea_envia_contacto_y_envuelve_la_respuesta() -> None:
    recibidas: list[httpx.Request] = []
    respuesta = {"results": {"bindings": [_fila("1", "Jaén")]}}

    def manejador(request: httpx.Request) -> httpx.Response:
        recibidas.append(request)
        return httpx.Response(200, json=respuesta)

    fuente = FuenteWikidataNombres(
        ["1"],
        contacto="https://ejemplo.test/contacto",
        cliente=cliente_simulado(manejador),
        politica=politica_sin_espera(),
        ahora=ahora_fijo,
    )

    nombres = fuente.obtener()

    assert nombres.por_geonameid == {"1": "Jaén"}
    assert nombres.descargado_en == ahora_fijo()
    peticion = recibidas[0]
    assert str(peticion.url) == URL
    assert peticion.method == "POST"
    assert "https://ejemplo.test/contacto" in peticion.headers["User-Agent"]
    assert fuente.id == "wikidata-en-linea"


def test_en_linea_rechazada_por_la_politica_de_robots() -> None:
    def prohibido(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Please respect our robot policy")

    fuente = FuenteWikidataNombres(
        ["1"],
        contacto="x@ejemplo.test",
        cliente=cliente_simulado(prohibido),
        politica=politica_sin_espera(),
    )
    with pytest.raises(FuenteNoDisponible, match="HTTP 403"):
        fuente.obtener()


def test_en_linea_respuesta_que_no_es_json() -> None:
    fuente = FuenteWikidataNombres(
        ["1"],
        contacto="x@ejemplo.test",
        cliente=cliente_simulado(lambda _: httpx.Response(200, text="error")),
        politica=politica_sin_espera(),
    )
    with pytest.raises(FuenteNoDisponible, match="no es JSON"):
        fuente.obtener()
