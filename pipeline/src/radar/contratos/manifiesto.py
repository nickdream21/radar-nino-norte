"""Manifiesto: índice de los productos publicados y su frescura."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Contrato(BaseModel):
    """Base de todos los contratos: inmutable y sin campos desconocidos."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        # Lo publicado siempre incluye los campos con valor por defecto, así que
        # el esquema que consume la web los declara obligatorios.
        json_schema_serialization_defaults_required=True,
    )


class ProductoPublicado(Contrato):
    """Un archivo de datos publicado para la web."""

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", description="Identificador estable.")
    ruta: str = Field(description="Ruta relativa al manifiesto.")
    fuente: str = Field(description="Origen de los datos, para la atribución.")
    actualizado_en: AwareDatetime = Field(description="Momento del dato más reciente.")
    vigencia_min: int = Field(
        gt=0, description="Minutos tras los cuales la web debe mostrar el dato como antiguo."
    )


class Manifiesto(Contrato):
    """Índice que la web lee primero para saber qué hay y qué tan reciente es."""

    version_esquema: Literal[1] = 1
    generado_en: AwareDatetime
    version_pipeline: str
    productos: list[ProductoPublicado] = Field(default_factory=list)
