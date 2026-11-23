"""Escritura de productos estáticos para la web."""

from radar.publicacion.escritor import escribir_json, publicar_manifiesto
from radar.publicacion.nino import FuentesNino, publicar_estado_nino

__all__ = ["FuentesNino", "escribir_json", "publicar_estado_nino", "publicar_manifiesto"]
