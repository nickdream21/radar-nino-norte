from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from radar.contratos import Manifiesto, ProductoPublicado
from radar.publicacion import publicar_manifiesto

AHORA = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def _producto(**cambios: object) -> ProductoPublicado:
    datos: dict[str, object] = {
        "id": "indices-nino",
        "ruta": "nino/indices.json",
        "fuente": "NOAA CPC",
        "actualizado_en": AHORA,
        "vigencia_min": 60,
    }
    return ProductoPublicado.model_validate(datos | cambios)


def test_publicar_manifiesto_se_puede_releer(tmp_path: Path) -> None:
    publicado = publicar_manifiesto(tmp_path, [_producto()], AHORA)

    releido = Manifiesto.model_validate_json(
        (tmp_path / "manifiesto.json").read_text(encoding="utf-8")
    )

    assert releido == publicado
    assert releido.productos[0].id == "indices-nino"


def test_publicar_no_deja_archivos_temporales(tmp_path: Path) -> None:
    publicar_manifiesto(tmp_path / "sub", [], AHORA)

    assert [p.name for p in (tmp_path / "sub").iterdir()] == ["manifiesto.json"]


@pytest.mark.parametrize(
    "cambios",
    [
        {"id": "Con Espacios"},
        {"vigencia_min": 0},
        {"actualizado_en": datetime(2026, 11, 23, 12, 0)},  # noqa: DTZ001 - sin zona a propósito
        {"campo_desconocido": 1},
    ],
)
def test_producto_rechaza_datos_invalidos(cambios: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _producto(**cambios)
