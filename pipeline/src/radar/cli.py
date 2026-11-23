"""Línea de comandos del pipeline: ``radar <orden>``."""

import argparse
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from radar.catalogo.cargar import NOMBRE_ARCHIVO as NOMBRE_CATALOGO
from radar.catalogo.generar import generar_archivo
from radar.catalogo.recalcular import cambios_de_zona, recalcular_archivo
from radar.catalogo.resumen import resumen_catalogo
from radar.contratos import CONTRATOS, ProductoPublicado
from radar.fuentes.crw_erddap import FuenteCrwMarPaita
from radar.fuentes.enfen import FuenteEnfenEstatica
from radar.fuentes.igp_icen import FuenteIgpIcen
from radar.fuentes.noaa_cpc import FuenteNoaaCpcSemanal
from radar.publicacion import FuentesNino, publicar_estado_nino, publicar_manifiesto

DATOS_ESTATICOS = Path(__file__).resolve().parents[3] / "datos-estaticos"
"""``datos-estaticos/`` en la raíz del repositorio (el pipeline se instala en modo editable)."""


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


def fuentes_nino(datos_estaticos: Path) -> FuentesNino:
    """Fuentes reales del estado de El Niño."""
    return FuentesNino(
        indices_semanales=FuenteNoaaCpcSemanal(),
        icen=FuenteIgpIcen(),
        mar_paita=FuenteCrwMarPaita(),
        enfen=FuenteEnfenEstatica(datos_estaticos / "enfen.json"),
    )


def publicar(destino: Path, fuentes: FuentesNino, ahora: datetime | None = None) -> None:
    """Genera los productos y el manifiesto en ``destino``.

    Un producto sin ningún dato que publicar no se registra en el manifiesto.
    """
    ahora = ahora or datetime.now(UTC)
    productos: list[ProductoPublicado] = []
    estado_nino = publicar_estado_nino(destino, fuentes, ahora)
    if estado_nino is not None:
        productos.append(estado_nino)
    publicar_manifiesto(destino, productos=productos, ahora=ahora)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="radar", description=__doc__)
    ordenes = analizador.add_subparsers(dest="orden", required=True)

    esquemas = ordenes.add_parser("exportar-esquemas", help="Exporta los JSON Schema.")
    esquemas.add_argument("--destino", type=Path, required=True)

    publicacion = ordenes.add_parser("publicar", help="Genera productos y manifiesto.")
    publicacion.add_argument("--destino", type=Path, required=True)
    publicacion.add_argument(
        "--datos-estaticos",
        type=Path,
        default=DATOS_ESTATICOS,
        help="Carpeta con los datos mantenidos a mano (por defecto, la del repositorio).",
    )

    distritos = ordenes.add_parser(
        "generar-distritos",
        help="Regenera el catálogo de distritos desde las fuentes (usa la red).",
    )
    distritos.add_argument(
        "--destino",
        type=Path,
        default=DATOS_ESTATICOS / NOMBRE_CATALOGO,
        help="Archivo de salida (por defecto, datos-estaticos/distritos.json).",
    )
    distritos.add_argument(
        "--instantanea-wikidata",
        type=Path,
        default=DATOS_ESTATICOS / "fuentes" / "wikidata-etiquetas.json",
        help="Etiquetas de Wikidata guardadas, de donde salen las tildes.",
    )
    distritos.add_argument(
        "--contacto-wikidata",
        help=(
            "URL o correo para el agente de usuario. Si se da, la instantánea de Wikidata"
            " se renueva en línea antes de generar (Wikimedia rechaza clientes sin contacto)."
        ),
    )

    recalculo = ordenes.add_parser(
        "recalcular-zonas",
        help="Recalcula zona y revisar del catálogo guardado con la regla vigente (sin red).",
    )
    recalculo.add_argument("--catalogo", type=Path, default=DATOS_ESTATICOS / NOMBRE_CATALOGO)

    argumentos = analizador.parse_args(argv)
    if argumentos.orden == "exportar-esquemas":
        for ruta in exportar_esquemas(argumentos.destino):
            print(ruta)
    elif argumentos.orden == "generar-distritos":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        catalogo, informe, comparaciones = generar_archivo(
            argumentos.destino,
            argumentos.instantanea_wikidata,
            contacto_wikidata=argumentos.contacto_wikidata,
        )
        print(resumen_catalogo(catalogo, informe, comparaciones))
    elif argumentos.orden == "recalcular-zonas":
        anterior, nuevo = recalcular_archivo(argumentos.catalogo)
        print("\n".join(cambios_de_zona(anterior, nuevo)) or "Ninguna zona cambia.")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        publicar(argumentos.destino, fuentes_nino(argumentos.datos_estaticos))
    return 0
