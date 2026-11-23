"""Línea de comandos del pipeline: ``radar <orden>``."""

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from radar.contratos import CONTRATOS
from radar.publicacion import publicar_manifiesto


def _quitar_titulos_de_campos(esquema: dict[str, Any]) -> None:
    """Quita el título de cada campo para que no se genere un alias de tipo por campo."""
    for definicion in (esquema, *esquema.get("$defs", {}).values()):
        for campo in definicion.get("properties", {}).values():
            campo.pop("title", None)


def exportar_esquemas(destino: Path) -> list[Path]:
    """Escribe un JSON Schema por contrato registrado y devuelve las rutas."""
    destino.mkdir(parents=True, exist_ok=True)
    rutas = []
    for nombre, contrato in sorted(CONTRATOS.items()):
        ruta = destino / f"{nombre}.schema.json"
        # "serialization": el esquema describe lo que el pipeline escribe, no lo que acepta.
        esquema = contrato.model_json_schema(mode="serialization")
        _quitar_titulos_de_campos(esquema)
        ruta.write_text(
            json.dumps(esquema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
        rutas.append(ruta)
    return rutas


def publicar(destino: Path) -> None:
    """Genera los productos y el manifiesto en ``destino``.

    En la Fase 0 todavía no hay fuentes conectadas: se publica un manifiesto
    vacío para que la web y el despliegue tengan un recorrido completo.
    """
    publicar_manifiesto(destino, productos=[], ahora=datetime.now(UTC))


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="radar", description=__doc__)
    ordenes = analizador.add_subparsers(dest="orden", required=True)

    esquemas = ordenes.add_parser("exportar-esquemas", help="Exporta los JSON Schema.")
    esquemas.add_argument("--destino", type=Path, required=True)

    publicacion = ordenes.add_parser("publicar", help="Genera productos y manifiesto.")
    publicacion.add_argument("--destino", type=Path, required=True)

    argumentos = analizador.parse_args(argv)
    if argumentos.orden == "exportar-esquemas":
        for ruta in exportar_esquemas(argumentos.destino):
            print(ruta)
    else:
        publicar(argumentos.destino)
    return 0
