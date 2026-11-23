"""Base común de los contratos y tipos compartidos."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict


class Contrato(BaseModel):
    """Base de todos los contratos: inmutable y sin campos desconocidos."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        # NaN e infinito nunca son un dato: indican un hueco que no se debe publicar.
        allow_inf_nan=False,
        # Lo publicado siempre incluye los campos con valor por defecto, así que
        # el esquema que consume la web los declara obligatorios.
        json_schema_serialization_defaults_required=True,
    )


def _a_utc(valor: datetime) -> datetime:
    return valor.astimezone(UTC)


FechaUtc = Annotated[AwareDatetime, AfterValidator(_a_utc)]
"""Fecha con zona horaria obligatoria; se guarda siempre convertida a UTC."""
