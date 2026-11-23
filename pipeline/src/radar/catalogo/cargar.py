"""Lectura y validación de ``datos-estaticos/distritos.json``."""

from pathlib import Path

from pydantic import ValidationError

from radar.catalogo.zonas import DatosZona, zona
from radar.contratos.distritos import CatalogoDistritos, Distrito, Zona

NOMBRE_ARCHIVO = "distritos.json"


class CatalogoInvalido(Exception):
    """El archivo del catálogo no existe, no cumple el contrato o contradice la regla de zonas."""


def zona_segun_regla(distrito: Distrito) -> Zona:
    """Zona que la regla asigna con los datos guardados del distrito."""
    return zona(
        DatosZona(
            ubigeo=distrito.ubigeo,
            altitud_m=distrito.capital.altitud_m,
            vertiente=distrito.vertiente,
            cuenca=distrito.cuenca,
            distancia_costa_km=distrito.distancia_costa_km,
            latitud=distrito.capital.latitud,
        )
    )


def cargar_catalogo(ruta: Path) -> CatalogoDistritos:
    """Lee el catálogo, lo valida contra el contrato y comprueba la zona de cada distrito."""
    try:
        catalogo = CatalogoDistritos.model_validate_json(ruta.read_text(encoding="utf-8"))
    except OSError as error:
        raise CatalogoInvalido(f"no se pudo leer {ruta}") from error
    except ValidationError as error:
        raise CatalogoInvalido(f"{ruta.name} no cumple el contrato: {error}") from error
    distintas = [
        f"{d.ubigeo} {d.nombre}: guardada {d.zona}, regla {zona_segun_regla(d)}"
        for d in catalogo.distritos
        if d.zona != zona_segun_regla(d)
    ]
    if distintas:
        raise CatalogoInvalido("zonas que no siguen la regla: " + "; ".join(distintas))
    return catalogo
