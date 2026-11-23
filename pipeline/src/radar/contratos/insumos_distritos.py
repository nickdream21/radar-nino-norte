"""Datos de entrada del catálogo de distritos, tal como los entrega cada fuente.

No se publican ni se exportan a la web: solo los validan los adaptadores de
``radar.fuentes`` antes de que ``radar.catalogo`` los combine en el catálogo.
"""

from typing import Self

from pydantic import Field, model_validator

from radar.contratos.base import Contrato, FechaUtc
from radar.contratos.distritos import Vertiente

Punto = tuple[float, float]
"""(longitud, latitud) en grados decimales, en el orden de GeoJSON."""


class DistritoOficial(Contrato):
    """Un distrito de la lista oficial del INEI, con los nombres como los escribe el INEI."""

    ubigeo: str = Field(pattern=r"^\d{6}$")
    departamento: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    nombre: str = Field(min_length=1)


class ListaDistritosOficial(Contrato):
    anio: int = Field(ge=2000, le=2100, description="Año de referencia de la lista.")
    distritos: list[DistritoOficial] = Field(min_length=1)

    @model_validator(mode="after")
    def _sin_repetidos(self) -> Self:
        ubigeos = [d.ubigeo for d in self.distritos]
        if len(set(ubigeos)) != len(ubigeos):
            raise ValueError("ubigeos repetidos en la lista oficial")
        return self


class CentroPoblado(Contrato):
    """Centro poblado censal del INEI (código de 4 dígitos dentro del distrito)."""

    ubigeo: str = Field(pattern=r"^\d{6}$")
    codigo: str = Field(pattern=r"^\d{4}$")
    nombre: str = Field(min_length=1)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class ListaCentrosPoblados(Contrato):
    centros: list[CentroPoblado]


class UnidadHidrografica(Contrato):
    """Unidad hidrográfica de la ANA (codificación Pfafstetter) con su contorno."""

    codigo: str = Field(pattern=r"^\d{1,8}$")
    nombre: str = Field(min_length=1)
    vertiente: Vertiente
    anillos: list[list[Punto]] = Field(
        min_length=1,
        description=(
            "Anillos del contorno (exteriores y huecos). Un punto está dentro si cruza"
            " un número impar de anillos, así que no hace falta saber cuál es cuál."
        ),
    )

    @model_validator(mode="after")
    def _anillos_cerrables(self) -> Self:
        if any(len(anillo) < 3 for anillo in self.anillos):
            raise ValueError("un anillo necesita al menos tres vértices")
        return self


class ListaUnidadesHidrograficas(Contrato):
    unidades: list[UnidadHidrografica] = Field(min_length=1)


class LineaCosta(Contrato):
    """Tramos de la línea de costa dentro de una caja."""

    tramos: list[list[Punto]] = Field(min_length=1)


class Elevaciones(Contrato):
    """Altitud en metros de cada punto pedido, en el mismo orden."""

    metros: list[float]


class LugarGeonames(Contrato):
    """Lugar de GeoNames (cabeceras de distrito y unidades administrativas)."""

    geonameid: str = Field(pattern=r"^\d+$")
    nombre: str = Field(min_length=1)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    clase: str = Field(min_length=1, description="Código de rasgo, p. ej. PPLA3 o ADM3.")
    ubigeo: str = Field(
        pattern=r"^\d{2}(\d{2}(\d{2})?)?$",
        description="Código administrativo (departamento, provincia o distrito).",
    )
    altitud_m: int | None = Field(description="Altitud declarada, si la hay.")
    altitud_mde_m: int | None = Field(description="Altitud del modelo de elevación de GeoNames.")


class ListaLugaresGeonames(Contrato):
    lugares: list[LugarGeonames] = Field(min_length=1)


class NombresWikidata(Contrato):
    """Etiqueta en español de Wikidata para cada identificador de GeoNames."""

    descargado_en: FechaUtc
    por_geonameid: dict[str, str]
