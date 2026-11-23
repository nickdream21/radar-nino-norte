from typing import Any

import pytest
from pydantic import ValidationError

from radar.contratos import CONTRATOS, CatalogoDistritos, Distrito
from tests.ayudas import AHORA


def _distrito(ubigeo: str = "240101", **cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ubigeo": ubigeo,
        "nombre": "Tumbes",
        "provincia": "Tumbes",
        "departamento": "Tumbes",
        "capital": {
            "nombre": "Tumbes",
            "latitud": -3.57,
            "longitud": -80.45,
            "altitud_m": 7,
            "fuente_ubicacion": "inei-ccpp",
        },
        "vertiente": "pacifico",
        "cuenca": "Cuenca Tumbes",
        "distancia_costa_km": 4.2,
        "zona": "B",
        "revisar": [],
    }
    return base | cambios


def _catalogo(*distritos: dict[str, Any]) -> dict[str, Any]:
    return {
        "generado_en": AHORA.isoformat(),
        "fuentes": [
            {
                "campos": "todos",
                "nombre": "Prueba",
                "url": "https://ejemplo.test",
                "licencia": "CC0 1.0",
                "atribucion": "Prueba",
                "descargado_en": AHORA.isoformat(),
            }
        ],
        "distritos": list(distritos),
    }


def test_registrado_en_contratos() -> None:
    assert CONTRATOS["catalogo_distritos"] is CatalogoDistritos


def test_catalogo_valido() -> None:
    catalogo = CatalogoDistritos.model_validate(
        _catalogo(_distrito(), _distrito("240102", nombre="Corrales"))
    )

    assert catalogo.version_esquema == 1
    assert len(catalogo.distritos) == 2


@pytest.mark.parametrize(
    ("cambios", "motivo"),
    [
        ({"ubigeo": "24011"}, "pattern"),
        ({"ubigeo": "150101"}, "no es de un departamento del proyecto"),
        ({"departamento": "Piura"}, "es de Tumbes, no de Piura"),
        ({"zona": "E"}, "literal_error"),
        ({"distancia_costa_km": float("nan")}, "finite_number"),
        ({"distancia_costa_km": -1}, "greater_than_equal"),
        ({"capital": _distrito()["capital"] | {"altitud_m": -9999}}, "greater_than_equal"),
        ({"capital": _distrito()["capital"] | {"latitud": None}}, "float_type"),
        ({"extra": 1}, "extra_forbidden"),
    ],
)
def test_distrito_invalido(cambios: dict[str, Any], motivo: str) -> None:
    with pytest.raises(ValidationError, match=motivo):
        Distrito.model_validate(_distrito(**cambios))


@pytest.mark.parametrize(
    ("distritos", "motivo"),
    [
        ((_distrito("240102"), _distrito("240101")), "ordenados"),
        ((_distrito(), _distrito()), "ordenados"),
        ((_distrito(), _distrito("240102", provincia="Otra")), "nombres distintos"),
        (
            (
                _distrito("200101", provincia="Tumbes", departamento="Piura"),
                _distrito(),
            ),
            "más de un departamento",
        ),
        ((), "too_short"),
    ],
)
def test_catalogo_incoherente(distritos: tuple[dict[str, Any], ...], motivo: str) -> None:
    with pytest.raises(ValidationError, match=motivo):
        CatalogoDistritos.model_validate(_catalogo(*distritos))


def test_fecha_sin_zona_horaria_se_rechaza() -> None:
    datos = _catalogo(_distrito()) | {"generado_en": "2026-11-23T15:00:00"}

    with pytest.raises(ValidationError):
        CatalogoDistritos.model_validate(datos)


def test_fecha_con_otra_zona_se_guarda_en_utc() -> None:
    datos = _catalogo(_distrito()) | {"generado_en": "2026-11-23T10:00:00-05:00"}

    assert CatalogoDistritos.model_validate(datos).generado_en == AHORA
