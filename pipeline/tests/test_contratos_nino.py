from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from radar.contratos import (
    BloqueEnfen,
    BloqueIcen,
    BloqueMarPaita,
    Caja,
    ComunicadoEnfen,
    IndiceSemanal,
    ValorMensual,
    ValorSemanal,
)
from radar.contratos.nino import MAX_SEMANAS

AHORA = datetime(2026, 11, 23, 12, tzinfo=UTC)
SEPT = ValorMensual(anio=2026, mes=9, fecha=datetime(2026, 9, 1, tzinfo=UTC), valor=4.5)
AGO = ValorMensual(anio=2026, mes=8, fecha=datetime(2026, 8, 1, tzinfo=UTC), valor=3.98)
CAJA = Caja(lat_min=-5.15, lat_max=-5.05, lon_min=-81.4, lon_max=-81.2)
COMUNICADO = ComunicadoEnfen(
    estado="Alerta de El Niño Costero",
    numero="20-2026",
    fecha=datetime(2026, 11, 13, 5, tzinfo=UTC),
    enlace="https://enfen.imarpe.gob.pe/",
)
BASE: dict[str, Any] = {
    "fuente": "prueba",
    "url": "https://ejemplo.test",
    "fecha_dato": AHORA,
    "obtenido_en": AHORA,
}


def _semana(dias: int) -> ValorSemanal:
    return ValorSemanal(
        fecha=datetime(2024, 1, 3, tzinfo=UTC) + timedelta(days=dias), temperatura=27, anomalia=1
    )


@pytest.mark.parametrize(
    ("contrato", "datos"),
    [
        (ValorSemanal, {"fecha": AHORA, "temperatura": float("nan"), "anomalia": 0}),
        (ValorSemanal, {"fecha": AHORA, "temperatura": 27, "anomalia": float("inf")}),
        (ValorSemanal, {"fecha": AHORA, "temperatura": 27, "anomalia": -99.99}),
        (
            ValorMensual,
            {"anio": 2026, "mes": 9, "fecha": datetime(2026, 8, 1, tzinfo=UTC), "valor": 1},
        ),
        (BloqueIcen, BASE | {"ultimo": SEPT, "serie": [SEPT, AGO]}),
        (BloqueIcen, BASE | {"ultimo": SEPT, "serie": [AGO]}),
        (Caja, {"lat_min": -5.05, "lat_max": -5.15, "lon_min": -81.4, "lon_max": -81.2}),
        (
            BloqueMarPaita,
            BASE | {"anomalia": 1, "caja": CAJA, "celdas_validas": 3, "celdas_totales": 2},
        ),
        (BloqueEnfen, BASE | {"comunicado": COMUNICADO}),
        (IndiceSemanal, {"ultimo": _semana(0), "serie": []}),
        (
            IndiceSemanal,
            {
                "ultimo": _semana(7 * MAX_SEMANAS),
                "serie": [_semana(7 * i) for i in range(MAX_SEMANAS + 1)],
            },
        ),
    ],
)
def test_contratos_rechazan_datos_incoherentes(
    contrato: type[BaseModel], datos: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        contrato.model_validate(datos)


def test_fechas_se_guardan_en_utc() -> None:
    lima = datetime.fromisoformat("2026-11-13T00:00:00-05:00")

    comunicado = COMUNICADO.model_copy(update={"fecha": lima})
    validado = ComunicadoEnfen.model_validate(comunicado.model_dump())

    assert validado.fecha.utcoffset() == timedelta(0)
    assert validado.fecha == lima


def test_bloque_icen_valido() -> None:
    bloque = BloqueIcen.model_validate(BASE | {"ultimo": SEPT, "serie": [AGO, SEPT]})

    assert bloque.ultimo == SEPT
