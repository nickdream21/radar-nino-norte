"""Generación completa del catálogo con las respuestas grabadas, sin red."""

import io
import json
import zipfile
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from radar import cli
from radar.catalogo import cargar_catalogo
from radar.catalogo.construir import CatalogoIncompleto
from radar.catalogo.generar import generar_archivo
from radar.catalogo.resumen import resumen_catalogo
from radar.fuentes import (
    ana_unidades_hidrograficas,
    inei_centros_poblados,
    inei_renamu,
    natural_earth,
    open_meteo_elevacion,
)
from radar.fuentes import geonames as fuente_geonames
from tests.ayudas import (
    ANA,
    COSTA,
    GEONAMES,
    INEI_CAPITALES,
    RENAMU,
    WIKIDATA,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
)

# Distritos de la muestra de capitales grabada: los cinco departamentos.
MUESTRA = {"060101", "060801", "130101", "130809", "140308", "200101", "200114", "240101"}
ALTITUD_FALSA = 150.0


def _zip(nombre: str, texto: str) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as archivo:
        archivo.writestr(nombre, texto.encode("utf-8"))
    return memoria.getvalue()


def _renamu(ubigeos: set[str]) -> str:
    cabecera, *filas = leer_fixture(RENAMU).splitlines()
    elegidas = [f for f in filas if f.split(";")[5].zfill(6) in ubigeos]
    return "\n".join([cabecera, *elegidas]) + "\n"


def _red(ubigeos: set[str] = MUESTRA) -> httpx.Client:
    respuestas = {
        inei_renamu.URL: _zip("Modulo1.csv", _renamu(ubigeos)),
        fuente_geonames.URL: _zip("PE.txt", leer_fixture(GEONAMES)),
        natural_earth.URL: leer_fixture(COSTA).encode(),
    }

    def manejador(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in respuestas:
            return httpx.Response(200, content=respuestas[url])
        if url.startswith(inei_centros_poblados.BASE):
            return httpx.Response(200, text=leer_fixture(INEI_CAPITALES))
        if url.startswith(ana_unidades_hidrograficas.BASE):
            return httpx.Response(200, text=leer_fixture(ANA))
        if url.startswith(open_meteo_elevacion.BASE):
            n = len(parse_qs(request.url.query.decode())["latitude"][0].split(","))
            return httpx.Response(200, json={"elevation": [ALTITUD_FALSA] * n})
        return httpx.Response(404)

    return cliente_simulado(manejador)


@pytest.fixture
def instantanea(tmp_path: Path) -> Path:
    ruta = tmp_path / "wikidata.json"
    ruta.write_text(leer_fixture(WIKIDATA), encoding="utf-8")
    return ruta


def test_genera_un_catalogo_valido(tmp_path: Path, instantanea: Path) -> None:
    destino = tmp_path / "distritos.json"

    catalogo, informe, comparaciones = generar_archivo(
        destino,
        instantanea,
        ahora=ahora_fijo,
        cliente=_red(),
        politica=politica_sin_espera(),
    )

    assert cargar_catalogo(destino) == catalogo
    por_ubigeo = {d.ubigeo: d for d in catalogo.distritos}
    assert set(por_ubigeo) == MUESTRA
    assert por_ubigeo["060801"].nombre == "Jaén"
    assert por_ubigeo["200114"].nombre == "Tambo Grande"
    assert por_ubigeo["240101"].zona == "B"
    assert all(d.capital.altitud_m == ALTITUD_FALSA for d in catalogo.distritos)
    assert all(d.capital.fuente_ubicacion == "inei-ccpp" for d in catalogo.distritos)
    assert catalogo.generado_en == ahora_fijo()
    assert len(catalogo.fuentes) == 7
    assert catalogo.fuentes[-1].campos == "capital.altitud_m"
    assert informe.capitales_sin_censo == []
    assert {c.ubigeo for c in comparaciones} <= MUESTRA
    assert comparaciones
    # Las capitales lejos de la cuenca grabada (Huarmaca) quedan marcadas, no forzadas.
    assert any("fuera de las unidades" in m for m in por_ubigeo["130809"].revisar)
    assert "Distritos: 8" in resumen_catalogo(catalogo, informe, comparaciones)


def test_distrito_posterior_al_censo_se_ubica_con_geonames(
    tmp_path: Path, instantanea: Path
) -> None:
    catalogo, informe, _ = generar_archivo(
        tmp_path / "distritos.json",
        instantanea,
        ahora=ahora_fijo,
        cliente=_red(MUESTRA | {"130112"}),
        politica=politica_sin_espera(),
    )

    alto = next(d for d in catalogo.distritos if d.ubigeo == "130112")
    assert alto.capital.fuente_ubicacion == "geonames"
    assert alto.nombre == "Alto Trujillo"
    assert any("GeoNames" in m for m in alto.revisar)
    assert informe.capitales_sin_censo == ["130112 Alto Trujillo"]


def test_capital_sin_ubicacion_detiene_la_generacion(tmp_path: Path, instantanea: Path) -> None:
    # Huanchaco no tiene capital en la muestra grabada ni un homónimo único en GeoNames.
    with pytest.raises(CatalogoIncompleto, match="130104"):
        generar_archivo(
            tmp_path / "distritos.json",
            instantanea,
            ahora=ahora_fijo,
            cliente=_red(MUESTRA | {"130104"}),
            politica=politica_sin_espera(),
        )
    assert not (tmp_path / "distritos.json").exists()


def test_orden_generar_distritos(
    tmp_path: Path,
    instantanea: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = generar_archivo

    def sin_red(destino: Path, instantanea: Path, *, contacto_wikidata: str | None) -> object:
        assert contacto_wikidata is None
        return original(
            destino,
            instantanea,
            ahora=ahora_fijo,
            cliente=_red(),
            politica=politica_sin_espera(),
        )

    monkeypatch.setattr(cli, "generar_archivo", sin_red)
    destino = tmp_path / "salida.json"

    codigo = cli.main(
        ["generar-distritos", "--destino", str(destino), "--instantanea-wikidata", str(instantanea)]
    )

    assert codigo == 0
    assert json.loads(destino.read_text(encoding="utf-8"))["version_esquema"] == 1
    assert "Caja de las capitales" in capsys.readouterr().out
