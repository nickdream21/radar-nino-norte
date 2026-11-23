"""Recalcula ``zona`` y ``revisar`` del catálogo guardado, sin red.

Cuando solo cambia la regla de zonas no hace falta volver a descargar las fuentes:
la regla usa campos que el archivo ya guarda (altitud, latitud, vertiente, cuenca y
distancia a la costa). Lo único que el archivo no guarda es la distancia de la
capital a la divisoria Pacífico-Atlántico; se recupera del motivo de revisión que la
anotó. Si un distrito no tiene ese motivo, su capital está a más de
``MARGEN_DIVISORIA_KM`` de la divisoria o la vertiente no le cambiaba la zona con
ninguna versión de la regla (en ambas vertientes era D, por encima de 3000 m), así
que la distancia no cuenta para la regla nueva.

Los motivos que vienen de cómo se ubicó la capital (``MOTIVOS_DE_UBICACION``) se
conservan tal cual; todos los demás se recalculan. El resto del archivo no cambia.
"""

import math
import re
from pathlib import Path

from pydantic import ValidationError

from radar.catalogo.cargar import CatalogoInvalido
from radar.catalogo.construir import MOTIVOS_DE_UBICACION
from radar.catalogo.zonas import MARGEN_DIVISORIA_KM, DatosZona, motivos_revision, zona
from radar.contratos.distritos import CatalogoDistritos, Distrito
from radar.publicacion.escritor import escribir_json

PATRON_DIVISORIA = re.compile(r"^capital a (\d+(?:\.\d+)?) km de la divisoria ")
"""Comienzo del motivo que escribe ``zonas.motivo_divisoria``."""


class RecalculoImposible(Exception):
    """El archivo guardado no permite recalcular sin volver a las fuentes."""


def distancia_divisoria_guardada(distrito: Distrito) -> float:
    """Distancia a la divisoria anotada en ``revisar``, o infinito si no se anotó."""
    distancias = [
        float(encontrado.group(1))
        for motivo in distrito.revisar
        if (encontrado := PATRON_DIVISORIA.match(motivo)) is not None
    ]
    if len(distancias) > 1:
        raise RecalculoImposible(f"{distrito.ubigeo}: más de un motivo de divisoria")
    if distancias and distancias[0] > MARGEN_DIVISORIA_KM:
        raise RecalculoImposible(
            f"{distrito.ubigeo}: divisoria a {distancias[0]} km, fuera del margen; el"
            " archivo no es de esta versión del generador"
        )
    return distancias[0] if distancias else math.inf


def recalcular_distrito(distrito: Distrito) -> Distrito:
    """El mismo distrito con ``zona`` y ``revisar`` según la regla vigente."""
    datos = DatosZona(
        ubigeo=distrito.ubigeo,
        altitud_m=distrito.capital.altitud_m,
        vertiente=distrito.vertiente,
        cuenca=distrito.cuenca,
        distancia_costa_km=distrito.distancia_costa_km,
        latitud=distrito.capital.latitud,
        distancia_divisoria_km=distancia_divisoria_guardada(distrito),
    )
    de_ubicacion = [m for m in distrito.revisar if m.startswith(MOTIVOS_DE_UBICACION)]
    return distrito.model_copy(
        update={"zona": zona(datos), "revisar": motivos_revision(datos) + de_ubicacion}
    )


def recalcular_zonas(catalogo: CatalogoDistritos) -> CatalogoDistritos:
    """Catálogo con zonas y motivos recalculados; todo lo demás queda igual."""
    distritos = [recalcular_distrito(d) for d in catalogo.distritos]
    return CatalogoDistritos.model_validate(
        catalogo.model_copy(update={"distritos": distritos}).model_dump()
    )


def recalcular_archivo(ruta: Path) -> tuple[CatalogoDistritos, CatalogoDistritos]:
    """Recalcula el catálogo de ``ruta`` en su sitio y devuelve el anterior y el nuevo.

    No usa ``cargar_catalogo``: el archivo guardado sigue la regla anterior.
    """
    try:
        anterior = CatalogoDistritos.model_validate_json(ruta.read_text(encoding="utf-8"))
    except OSError as error:
        raise CatalogoInvalido(f"no se pudo leer {ruta}") from error
    except ValidationError as error:
        raise CatalogoInvalido(f"{ruta.name} no cumple el contrato: {error}") from error
    nuevo = recalcular_zonas(anterior)
    escribir_json(nuevo, ruta)
    return anterior, nuevo


def cambios_de_zona(anterior: CatalogoDistritos, nuevo: CatalogoDistritos) -> list[str]:
    """Una línea por distrito que cambia de zona, para revisar el recálculo."""
    return [
        f"{a.ubigeo} {a.nombre}: {a.zona} -> {n.zona}"
        for a, n in zip(anterior.distritos, nuevo.distritos, strict=True)
        if a.zona != n.zona
    ]
