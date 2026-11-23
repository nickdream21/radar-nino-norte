"""Catálogo de distritos del norte (``datos-estaticos/distritos.json``).

Lista oficial de distritos de Tumbes, Piura, Lambayeque, La Libertad y Cajamarca
con la ubicación y la altitud de su capital y su zona pluviométrica. El pipeline
lo usa para pronosticar por distrito y la web lo lleva dentro para elegir el
distrito sin conexión. Se regenera con ``radar generar-distritos``.
"""

from itertools import pairwise
from typing import Literal, Self

from pydantic import Field, model_validator

from radar.contratos.base import Contrato, FechaUtc

Zona = Literal["A", "B", "C", "D"]
"""A costa árida, B Tumbes y piedemonte, C sierra occidental, D sierra alta y vertiente oriental."""

Vertiente = Literal["pacifico", "atlantico"]
"""Región hidrográfica a la que drena la capital: Pacífico, o Amazonas (cuenca del Marañón)."""

FuenteUbicacion = Literal["inei-ccpp", "geonames"]
"""De dónde salen las coordenadas de la capital (ver ``fuentes`` del catálogo)."""

DEPARTAMENTOS: dict[str, str] = {
    "06": "Cajamarca",
    "13": "La Libertad",
    "14": "Lambayeque",
    "20": "Piura",
    "24": "Tumbes",
}
"""Código INEI de departamento y su nombre: los cinco que cubre el proyecto."""


class CapitalDistrital(Contrato):
    """Capital del distrito: el punto que representa al distrito en los pronósticos."""

    nombre: str = Field(min_length=1)
    latitud: float = Field(ge=-90, le=90, description="Grados decimales, WGS 84.")
    longitud: float = Field(ge=-180, le=180, description="Grados decimales, WGS 84.")
    altitud_m: int = Field(
        ge=-50, le=6000, description="Metros sobre el nivel del mar, del modelo de elevación."
    )
    fuente_ubicacion: FuenteUbicacion


class Distrito(Contrato):
    """Un distrito con su capital y su zona pluviométrica."""

    ubigeo: str = Field(pattern=r"^\d{6}$", description="Código INEI de 6 dígitos.")
    nombre: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    departamento: str = Field(min_length=1)
    capital: CapitalDistrital
    vertiente: Vertiente
    cuenca: str = Field(
        min_length=1, description="Unidad hidrográfica (ANA) en la que está la capital."
    )
    distancia_costa_km: float = Field(ge=0, description="De la capital a la línea de costa.")
    zona: Zona = Field(description="Calculada con la regla de zonas, nunca escrita a mano.")
    revisar: list[str] = Field(
        description=(
            "Motivos por los que la zona es dudosa o fronteriza y debe revisarla el"
            " meteorólogo. Vacía si la regla se aplica sin ambigüedad."
        )
    )

    @model_validator(mode="after")
    def _departamento_coherente(self) -> Self:
        esperado = DEPARTAMENTOS.get(self.ubigeo[:2])
        if esperado is None:
            raise ValueError(f"el ubigeo {self.ubigeo} no es de un departamento del proyecto")
        if self.departamento != esperado:
            raise ValueError(f"el ubigeo {self.ubigeo} es de {esperado}, no de {self.departamento}")
        return self


class FuenteCatalogo(Contrato):
    """Procedencia de uno o varios campos del catálogo."""

    campos: str = Field(min_length=1, description="Campos que aporta esta fuente.")
    nombre: str = Field(min_length=1)
    url: str = Field(pattern=r"^https?://")
    licencia: str = Field(min_length=1)
    atribucion: str = Field(min_length=1)
    descargado_en: FechaUtc


class CatalogoDistritos(Contrato):
    """Todos los distritos de los cinco departamentos, ordenados por ubigeo."""

    version_esquema: Literal[1] = 1
    generado_en: FechaUtc
    fuentes: list[FuenteCatalogo] = Field(min_length=1)
    distritos: list[Distrito] = Field(min_length=1)

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        ubigeos = [d.ubigeo for d in self.distritos]
        if any(a >= b for a, b in pairwise(ubigeos)):
            raise ValueError("los distritos deben estar ordenados por ubigeo y sin repetir")
        provincias: dict[str, tuple[str, str]] = {}
        for distrito in self.distritos:
            clave = distrito.ubigeo[:4]
            nombres = (distrito.provincia, distrito.departamento)
            if provincias.setdefault(clave, nombres) != nombres:
                raise ValueError(f"la provincia {clave} tiene nombres distintos")
        departamentos_por_provincia: dict[str, set[str]] = {}
        for provincia, departamento in provincias.values():
            departamentos_por_provincia.setdefault(provincia, set()).add(departamento)
        repetidas = sorted(p for p, ds in departamentos_por_provincia.items() if len(ds) > 1)
        if repetidas:
            raise ValueError(f"provincias en más de un departamento: {repetidas}")
        return self
