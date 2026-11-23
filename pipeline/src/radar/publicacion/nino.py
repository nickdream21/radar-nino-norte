"""Producto ``nino/estado.json``: estado observado de El Niño.

Cada bloque se obtiene por separado. Si su fuente falla se conserva el bloque de
la publicación anterior (que el flujo de ingesta deja en la carpeta de destino) y,
si no lo hay, el bloque se publica como ausente. Nunca se rellena ni se interpola.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from radar.contratos import (
    BloqueEnfen,
    BloqueIcen,
    BloqueIndicesSemanales,
    BloqueMarPaita,
    EstadoNino,
    ProductoPublicado,
)
from radar.fuentes import FuenteDatos, FuenteNoDisponible
from radar.publicacion.escritor import escribir_json

registro = logging.getLogger(__name__)

ID_PRODUCTO = "estado-nino"
RUTA_ESTADO = "nino/estado.json"

VIGENCIA_MIN = 4 * 24 * 60
"""Cuatro días, medidos desde el dato más reciente del producto.

El bloque más rápido es la anomalía diaria de Coral Reef Watch, que llega con unos
dos días de retraso; con una ingesta diaria, ``actualizado_en`` va normalmente de
dos a tres días por detrás. Pasados cuatro días se han perdido al menos dos
actualizaciones seguidas y la web debe marcar el producto como antiguo. Los
bloques semanales, mensuales y del ENFEN llevan su propia fecha para que la web
juzgue cada uno a su ritmo.
"""


@dataclass(frozen=True)
class FuentesNino:
    """Las fuentes de cada bloque del estado de El Niño."""

    indices_semanales: FuenteDatos[BloqueIndicesSemanales]
    icen: FuenteDatos[BloqueIcen]
    mar_paita: FuenteDatos[BloqueMarPaita]
    enfen: FuenteDatos[BloqueEnfen]


def leer_anterior(ruta: Path) -> EstadoNino | None:
    """Lee la publicación previa, o ``None`` si no existe o no es válida."""
    if not ruta.exists():
        return None
    try:
        return EstadoNino.model_validate_json(ruta.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        registro.warning("No se puede reutilizar %s: %s", ruta, error)
        return None


def _obtener[T](fuente: FuenteDatos[T], previo: T | None) -> T | None:
    try:
        return fuente.obtener()
    except (FuenteNoDisponible, ValidationError) as error:
        # Un ValidationError aquí es un dato de la fuente que no cumple el contrato.
        if previo is None:
            registro.error("%s falló y no hay dato anterior: %s", fuente.id, error)
        else:
            registro.warning("%s falló, se conserva el dato anterior: %s", fuente.id, error)
        return previo


def construir_estado_nino(
    fuentes: FuentesNino, anterior: EstadoNino | None, ahora: datetime
) -> EstadoNino | None:
    """Combina las fuentes en el estado; ``None`` si no hay ningún bloque que publicar."""
    estado = EstadoNino(
        generado_en=ahora,
        indices_semanales=_obtener(
            fuentes.indices_semanales, anterior.indices_semanales if anterior else None
        ),
        icen=_obtener(fuentes.icen, anterior.icen if anterior else None),
        mar_paita=_obtener(fuentes.mar_paita, anterior.mar_paita if anterior else None),
        enfen=_obtener(fuentes.enfen, anterior.enfen if anterior else None),
    )
    return estado if estado.bloques() else None


def publicar_estado_nino(
    carpeta: Path, fuentes: FuentesNino, ahora: datetime
) -> ProductoPublicado | None:
    """Escribe ``nino/estado.json`` y devuelve su entrada del manifiesto.

    Devuelve ``None`` (y no escribe nada) si todas las fuentes fallan y no había
    una publicación anterior.
    """
    ruta = carpeta / RUTA_ESTADO
    estado = construir_estado_nino(fuentes, leer_anterior(ruta), ahora)
    if estado is None:
        registro.error("Ningún bloque disponible: %s no se publica", RUTA_ESTADO)
        return None
    escribir_json(estado, ruta)
    bloques = estado.bloques()
    return ProductoPublicado(
        id=ID_PRODUCTO,
        ruta=RUTA_ESTADO,
        fuente="; ".join(dict.fromkeys(b.fuente for b in bloques)),
        actualizado_en=max(b.fecha_dato for b in bloques),
        vigencia_min=VIGENCIA_MIN,
    )
