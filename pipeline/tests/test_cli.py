import json
from pathlib import Path

import pytest

from radar import cli
from radar.cli import DATOS_ESTATICOS, fuentes_nino, main, publicar
from radar.contratos import CONTRATOS, EstadoNino, Manifiesto
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.crw_erddap import FuenteCrwMarPaita
from radar.fuentes.enfen import FuenteEnfenEstatica
from radar.fuentes.http import PoliticaReintentos
from radar.fuentes.igp_icen import FuenteIgpIcen
from radar.fuentes.noaa_cpc import FuenteNoaaCpcSemanal
from radar.publicacion import FuentesNino


def test_exportar_esquemas_escribe_uno_por_contrato(tmp_path: Path) -> None:
    assert main(["exportar-esquemas", "--destino", str(tmp_path)]) == 0

    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == sorted(f"{n}.schema.json" for n in CONTRATOS)
    esquema = json.loads((tmp_path / "manifiesto.schema.json").read_text(encoding="utf-8"))
    assert esquema["title"] == "Manifiesto"
    # La web recibe siempre los campos con valor por defecto: deben ser obligatorios.
    assert set(esquema["required"]) == set(esquema["properties"])
    assert all("title" not in campo for campo in esquema["properties"].values())


def test_esquema_estado_nino_declara_los_bloques_obligatorios_y_anulables(
    tmp_path: Path,
) -> None:
    main(["exportar-esquemas", "--destino", str(tmp_path)])

    esquema = json.loads((tmp_path / "estado_nino.schema.json").read_text(encoding="utf-8"))
    assert set(esquema["required"]) == set(esquema["properties"])
    for bloque in ("indices_semanales", "icen", "mar_paita", "enfen"):
        tipos = [opcion.get("type") for opcion in esquema["properties"][bloque]["anyOf"]]
        assert "null" in tipos


def test_publicar_sin_red_registra_solo_lo_disponible(tmp_path: Path) -> None:
    # La red está bloqueada en las pruebas: solo el bloque ENFEN (archivo local) se publica.
    rapida = PoliticaReintentos(intentos=1)
    fuentes = FuentesNino(
        indices_semanales=FuenteNoaaCpcSemanal(politica=rapida),
        icen=FuenteIgpIcen(politica=rapida),
        mar_paita=FuenteCrwMarPaita(politica=rapida),
        enfen=FuenteEnfenEstatica(DATOS_ESTATICOS / "enfen.json"),
    )

    publicar(tmp_path, fuentes)

    manifiesto = Manifiesto.model_validate_json(
        (tmp_path / "manifiesto.json").read_text(encoding="utf-8")
    )
    assert [p.id for p in manifiesto.productos] == ["estado-nino"]
    estado = EstadoNino.model_validate_json(
        (tmp_path / "nino" / "estado.json").read_text(encoding="utf-8")
    )
    assert estado.enfen is not None
    assert estado.indices_semanales is None


def test_main_publicar_sin_ningun_dato_deja_el_manifiesto_vacio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def ninguna(_: Path) -> FuentesNino:
        caida = FuenteEnfenEstatica(tmp_path / "no-existe.json")
        return FuentesNino(
            indices_semanales=FuenteNoaaCpcSemanal(politica=PoliticaReintentos(intentos=1)),
            icen=FuenteIgpIcen(politica=PoliticaReintentos(intentos=1)),
            mar_paita=FuenteCrwMarPaita(politica=PoliticaReintentos(intentos=1)),
            enfen=caida,
        )

    monkeypatch.setattr(cli, "fuentes_nino", ninguna)

    assert main(["publicar", "--destino", str(tmp_path / "salida")]) == 0

    manifiesto = Manifiesto.model_validate_json(
        (tmp_path / "salida" / "manifiesto.json").read_text(encoding="utf-8")
    )
    assert manifiesto.productos == []
    assert not (tmp_path / "salida" / "nino").exists()


def test_fuentes_reales_apuntan_a_los_datos_estaticos(tmp_path: Path) -> None:
    fuentes = fuentes_nino(tmp_path)

    assert fuentes.enfen.id == "enfen-estatico"
    assert {f.id for f in (fuentes.indices_semanales, fuentes.icen, fuentes.mar_paita)} == {
        "noaa-cpc-semanal",
        "igp-icen",
        "crw-mar-paita",
    }


def test_orden_desconocida_falla() -> None:
    with pytest.raises(SystemExit):
        main(["no-existe"])


def test_fuente_no_disponible_conserva_fuente_y_motivo() -> None:
    error = FuenteNoDisponible("noaa-cpc", "tiempo de espera agotado")

    assert error.fuente == "noaa-cpc"
    assert str(error) == "noaa-cpc: tiempo de espera agotado"
