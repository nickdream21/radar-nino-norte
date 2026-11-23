"""Catálogo de distritos: regla de zonas, armado desde las fuentes y lectura validada."""

from radar.catalogo.cargar import CatalogoInvalido, cargar_catalogo, zona_segun_regla
from radar.catalogo.zonas import DatosZona, motivos_revision, zona

__all__ = [
    "CatalogoInvalido",
    "DatosZona",
    "cargar_catalogo",
    "motivos_revision",
    "zona",
    "zona_segun_regla",
]
