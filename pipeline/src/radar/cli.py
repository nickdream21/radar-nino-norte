"""Línea de comandos del pipeline: ``radar <orden>``."""

import argparse
import json
import logging
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from radar.catalogo import CatalogoInvalido, cargar_catalogo
from radar.catalogo.cargar import NOMBRE_ARCHIVO as NOMBRE_CATALOGO
from radar.catalogo.generar import generar_archivo
from radar.catalogo.recalcular import cambios_de_zona, recalcular_archivo
from radar.catalogo.resumen import resumen_catalogo
from radar.contratos import CONTRATOS, ArchivoLluvia, ProductoPublicado
from radar.fuentes.crw_erddap import FuenteCrwMarPaita
from radar.fuentes.enfen import FuenteEnfenEstatica
from radar.fuentes.igp_icen import FuenteIgpIcen
from radar.fuentes.noaa_cpc import FuenteNoaaCpcSemanal
from radar.publicacion import FuentesNino, publicar_estado_nino, publicar_manifiesto
from radar.publicacion.lluvia import RUTA_PRODUCTO as RUTA_LLUVIA
from radar.publicacion.lluvia import (
    FuentesLluvia,
    fuentes_lluvia_reales,
    leer_producto,
    publicar_lluvia,
)
from radar.publicacion.lluvia import entrada_manifiesto as entrada_lluvia

registro = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[3]
DATOS_ESTATICOS = RAIZ / "datos-estaticos"
"""``datos-estaticos/`` en la raíz del repositorio (el pipeline se instala en modo editable)."""
ESQUEMA_ARCHIVO = RAIZ / "docs" / "esquemas" / "archivo_lluvia.schema.json"
"""Esquema del archivo de pronósticos: no es un producto para la web y no genera tipos."""


def _quitar_titulos_de_campos(esquema: dict[str, Any]) -> None:
    """Quita el título de cada campo para que no se genere un alias de tipo por campo."""
    for definicion in (esquema, *esquema.get("$defs", {}).values()):
        for campo in definicion.get("properties", {}).values():
            campo.pop("title", None)


def escribir_esquema(contrato: type[BaseModel], ruta: Path) -> None:
    """JSON Schema de lo que el pipeline escribe (modo "serialization")."""
    esquema = contrato.model_json_schema(mode="serialization")
    _quitar_titulos_de_campos(esquema)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(esquema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def exportar_esquemas(destino: Path) -> list[Path]:
    """Escribe un JSON Schema por contrato registrado y devuelve las rutas."""
    rutas = []
    for nombre, contrato in sorted(CONTRATOS.items()):
        ruta = destino / f"{nombre}.schema.json"
        escribir_esquema(contrato, ruta)
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


def fuentes_lluvia(datos_estaticos: Path) -> FuentesLluvia | None:
    """Fuentes reales de la lluvia por distrito; ``None`` si el catálogo no es válido."""
    try:
        catalogo = cargar_catalogo(datos_estaticos / NOMBRE_CATALOGO)
    except CatalogoInvalido as error:
        registro.error("Lluvia: catálogo de distritos inválido: %s", error)
        return None
    return fuentes_lluvia_reales(catalogo)


def _lluvia_aislada(
    destino: Path, lluvia: FuentesLluvia | None, ahora: datetime, archivo: Path | None
) -> ProductoPublicado | None:
    """Publica la lluvia sin que un fallo inesperado afecte a los demás productos."""
    try:
        if lluvia is not None:
            return publicar_lluvia(
                destino,
                lluvia,
                ahora,
                carpeta_archivo=archivo,
                commit=os.environ.get("GITHUB_SHA"),
            )
    except Exception:
        registro.exception("Lluvia: error inesperado; se conserva el producto anterior")
    anterior = leer_producto(destino / RUTA_LLUVIA)
    return None if anterior is None else entrada_lluvia(anterior)


def publicar(
    destino: Path,
    fuentes: FuentesNino,
    ahora: datetime | None = None,
    *,
    lluvia: FuentesLluvia | None = None,
    archivo: Path | None = None,
) -> None:
    """Genera los productos y el manifiesto en ``destino``.

    Un producto sin ningún dato que publicar no se registra en el manifiesto. Sin
    ``lluvia`` se conserva el producto de lluvia anterior, si lo hay.
    """
    ahora = ahora or datetime.now(UTC)
    productos: list[ProductoPublicado] = []
    estado_nino = publicar_estado_nino(destino, fuentes, ahora)
    if estado_nino is not None:
        productos.append(estado_nino)
    lluvia_distritos = _lluvia_aislada(destino, lluvia, ahora, archivo)
    if lluvia_distritos is not None:
        productos.append(lluvia_distritos)
    publicar_manifiesto(destino, productos=productos, ahora=ahora)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(prog="radar", description=__doc__)
    ordenes = analizador.add_subparsers(dest="orden", required=True)

    esquemas = ordenes.add_parser("exportar-esquemas", help="Exporta los JSON Schema.")
    esquemas.add_argument("--destino", type=Path, required=True)

    esquema_archivo = ordenes.add_parser(
        "exportar-esquema-archivo", help="Exporta el esquema del archivo de pronósticos."
    )
    esquema_archivo.add_argument("--destino", type=Path, default=ESQUEMA_ARCHIVO)

    publicacion = ordenes.add_parser("publicar", help="Genera productos y manifiesto.")
    publicacion.add_argument("--destino", type=Path, required=True)
    publicacion.add_argument(
        "--datos-estaticos",
        type=Path,
        default=DATOS_ESTATICOS,
        help="Carpeta con los datos mantenidos a mano (por defecto, la del repositorio).",
    )
    publicacion.add_argument(
        "--archivo",
        type=Path,
        help=(
            "Carpeta del archivo de corridas por subir (por defecto, <destino>/archivo-pendiente)."
        ),
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
    elif argumentos.orden == "exportar-esquema-archivo":
        escribir_esquema(ArchivoLluvia, argumentos.destino)
        print(argumentos.destino)
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
        logging.getLogger("httpx").setLevel(logging.WARNING)
        publicar(
            argumentos.destino,
            fuentes_nino(argumentos.datos_estaticos),
            lluvia=fuentes_lluvia(argumentos.datos_estaticos),
            archivo=argumentos.archivo,
        )
    return 0
