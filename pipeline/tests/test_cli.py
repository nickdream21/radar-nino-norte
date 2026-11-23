import json
from pathlib import Path

import pytest

from radar.cli import main
from radar.contratos import CONTRATOS, Manifiesto
from radar.fuentes import FuenteNoDisponible


def test_exportar_esquemas_escribe_uno_por_contrato(tmp_path: Path) -> None:
    assert main(["exportar-esquemas", "--destino", str(tmp_path)]) == 0

    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == sorted(f"{n}.schema.json" for n in CONTRATOS)
    esquema = json.loads((tmp_path / "manifiesto.schema.json").read_text(encoding="utf-8"))
    assert esquema["title"] == "Manifiesto"
    # La web recibe siempre los campos con valor por defecto: deben ser obligatorios.
    assert set(esquema["required"]) == set(esquema["properties"])
    assert all("title" not in campo for campo in esquema["properties"].values())


def test_publicar_genera_manifiesto_valido(tmp_path: Path) -> None:
    assert main(["publicar", "--destino", str(tmp_path)]) == 0

    manifiesto = Manifiesto.model_validate_json(
        (tmp_path / "manifiesto.json").read_text(encoding="utf-8")
    )
    assert manifiesto.productos == []


def test_orden_desconocida_falla() -> None:
    with pytest.raises(SystemExit):
        main(["no-existe"])


def test_fuente_no_disponible_conserva_fuente_y_motivo() -> None:
    error = FuenteNoDisponible("noaa-cpc", "tiempo de espera agotado")

    assert error.fuente == "noaa-cpc"
    assert str(error) == "noaa-cpc: tiempo de espera agotado"
