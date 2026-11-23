"""Escritura atómica de productos y del manifiesto."""

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from radar import __version__
from radar.contratos import Manifiesto, ProductoPublicado

NOMBRE_MANIFIESTO = "manifiesto.json"


def escribir_json(modelo: BaseModel, destino: Path) -> None:
    """Escribe ``modelo`` como JSON sin dejar nunca un archivo a medias.

    La web puede leer el archivo en cualquier momento, así que se escribe a un
    temporal en la misma carpeta y se reemplaza de una sola vez.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    temporal.write_text(modelo.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
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
