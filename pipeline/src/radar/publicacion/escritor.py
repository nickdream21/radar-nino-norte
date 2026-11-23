"""Escritura atómica de productos y del manifiesto."""

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from radar import __version__
from radar.contratos import Manifiesto, ProductoPublicado

NOMBRE_MANIFIESTO = "manifiesto.json"


def escribir_json(modelo: BaseModel, destino: Path, *, compacto: bool = False) -> None:
    """Escribe ``modelo`` como JSON sin dejar nunca un archivo a medias.

    La web puede leer el archivo en cualquier momento, así que se escribe a un
    temporal en la misma carpeta y se reemplaza de una sola vez. ``compacto`` omite
    la sangría en productos grandes que se descargan desde el celular.
    """
    escribir_bytes(
        (modelo.model_dump_json(indent=None if compacto else 2) + "\n").encode("utf-8"), destino
    )


def escribir_bytes(contenido: bytes, destino: Path) -> None:
    """Escritura atómica de ``contenido`` en ``destino``."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    temporal.write_bytes(contenido)
    temporal.replace(destino)


def publicar_manifiesto(
    carpeta: Path, productos: Sequence[ProductoPublicado], ahora: datetime
) -> Manifiesto:
    """Escribe el manifiesto de ``productos`` en ``carpeta`` y lo devuelve."""
    manifiesto = Manifiesto(
        generado_en=ahora,
        version_pipeline=__version__,
        productos=list(productos),
    )
    escribir_json(manifiesto, carpeta / NOMBRE_MANIFIESTO)
    return manifiesto
