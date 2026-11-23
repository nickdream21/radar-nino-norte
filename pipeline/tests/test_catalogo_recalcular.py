"""Recálculo de zonas del catálogo guardado, sin red."""

import json
import math
from pathlib import Path

import pytest

from radar import cli
from radar.catalogo import CatalogoInvalido, cargar_catalogo
from radar.catalogo.cargar import NOMBRE_ARCHIVO
from radar.catalogo.construir import MOTIVO_CAPITAL_GEONAMES
from radar.catalogo.generar import generar_archivo
from radar.catalogo.recalcular import (
    RecalculoImposible,
    distancia_divisoria_guardada,
    recalcular_archivo,
    recalcular_distrito,
    recalcular_zonas,
)
from radar.catalogo.zonas import motivo_divisoria
from radar.cli import DATOS_ESTATICOS
from radar.contratos.distritos import CapitalDistrital, Distrito
from tests.ayudas import WIKIDATA, ahora_fijo, leer_fixture, politica_sin_espera
from tests.test_catalogo_generar import MUESTRA, _red

RUTA = DATOS_ESTATICOS / NOMBRE_ARCHIVO


def _distrito(
    revisar: list[str], altitud_m: int = 2166, zona: str = "A", vertiente: str = "pacifico"
) -> Distrito:
    return Distrito.model_validate(
        {
            "ubigeo": "200304",
            "nombre": "Huarmaca",
            "provincia": "Huancabamba",
            "departamento": "Piura",
            "capital": CapitalDistrital(
                nombre="Huarmaca",
                latitud=-5.56797,
                longitud=-79.52,
                altitud_m=altitud_m,
                fuente_ubicacion="inei-ccpp",
            ),
            "vertiente": vertiente,
            "cuenca": "Cuenca Piura",
            "distancia_costa_km": 136.9,
            "zona": zona,
            "revisar": revisar,
        }
    )


def test_el_motivo_de_divisoria_se_relee() -> None:
    distrito = _distrito([motivo_divisoria(0.1, "D")])

    assert distancia_divisoria_guardada(distrito) == 0.1
    assert distancia_divisoria_guardada(_distrito([])) == math.inf


def test_divisoria_fuera_del_margen_no_se_acepta() -> None:
    with pytest.raises(RecalculoImposible, match="fuera del margen"):
        distancia_divisoria_guardada(_distrito([motivo_divisoria(7.2, "D")]))


def test_recalcula_zona_y_motivos_y_conserva_los_de_ubicacion() -> None:
    viejo = _distrito(
        [
            motivo_divisoria(0.1, "D"),
            "altitud 2166 m: motivo de una regla anterior",
            MOTIVO_CAPITAL_GEONAMES,
        ]
    )

    nuevo = recalcular_distrito(viejo)

    assert nuevo.zona == "C"
    assert nuevo.revisar == [motivo_divisoria(0.1, "D"), MOTIVO_CAPITAL_GEONAMES]
    assert nuevo.model_dump(exclude={"zona", "revisar"}) == viejo.model_dump(
        exclude={"zona", "revisar"}
    )


def test_la_divisoria_deja_de_importar_si_ambas_vertientes_dan_lo_mismo() -> None:
    # A 1200 m es C en el Atlántico y en el Pacífico: el motivo desaparece.
    nuevo = recalcular_distrito(_distrito([motivo_divisoria(0.1, "D")], altitud_m=1200))

    assert nuevo.zona == "C"
    assert nuevo.revisar == []


def test_recalcular_lo_recien_generado_no_cambia_nada(tmp_path: Path) -> None:
    instantanea = tmp_path / "wikidata.json"
    instantanea.write_text(leer_fixture(WIKIDATA), encoding="utf-8")
    catalogo, _, _ = generar_archivo(
        tmp_path / NOMBRE_ARCHIVO,
        instantanea,
        ahora=ahora_fijo,
        cliente=_red(MUESTRA | {"130112"}),
        politica=politica_sin_espera(),
    )

    assert recalcular_zonas(catalogo) == catalogo


def test_el_archivo_confirmado_ya_esta_recalculado() -> None:
    catalogo = cargar_catalogo(RUTA)

    assert recalcular_zonas(catalogo) == catalogo


def test_orden_recalcular_zonas(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    jaen = next(d for d in datos["distritos"] if d["ubigeo"] == "060801")
    jaen["zona"] = "D"
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assert cli.main(["recalcular-zonas", "--catalogo", str(ruta)]) == 0

    assert capsys.readouterr().out.strip() == "060801 Jaén: D -> C"
    assert ruta.read_text(encoding="utf-8") == RUTA.read_text(encoding="utf-8")


def test_recalcular_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(CatalogoInvalido, match="no se pudo leer"):
        recalcular_archivo(tmp_path / NOMBRE_ARCHIVO)


def test_recalcular_archivo_que_no_cumple_el_contrato(tmp_path: Path) -> None:
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text('{"version_esquema": 1}', encoding="utf-8")

    with pytest.raises(CatalogoInvalido, match="no cumple el contrato"):
        recalcular_archivo(ruta)


def test_dos_motivos_de_divisoria_no_se_aceptan() -> None:
    motivos = [motivo_divisoria(0.1, "D"), motivo_divisoria(0.2, "D")]

    with pytest.raises(RecalculoImposible, match="más de un motivo"):
        distancia_divisoria_guardada(_distrito(motivos))
