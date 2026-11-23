"""Wikidata (CC0): nombre en español de lugares identificados por su GeoNames ID.

El INEI escribe los nombres en mayúsculas y sin tildes. Las etiquetas en español
de Wikidata los tienen con su ortografía, pero Wikidata no guarda el ubigeo INEI
(su propiedad P844 usa el código del RENIEC), así que el enlace se hace por el
identificador de GeoNames (P1566). Solo se toman las tildes, y solo si la etiqueta
coincide letra por letra con el nombre del INEI (ver ``radar.catalogo.nombres``).

El servicio SPARQL de Wikimedia rechaza con 403 a los clientes de programa sin un
agente de usuario con datos de contacto. Por eso el catálogo no lo consulta en
cada regeneración: lee una instantánea guardada en el repositorio
(``datos-estaticos/fuentes/wikidata-etiquetas.json``) con ``FuenteWikidataArchivo``,
y ``FuenteWikidataNombres`` la renueva en línea cuando se le da un contacto.

Respuesta SPARQL JSON::

    {"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q..."},
                               "gn": {"value": "3691148"},
                               "l": {"xml:lang": "es", "value": "Distrito de Tumbes"}}]}}

La instantánea envuelve esa respuesta con su fecha y su consulta::

    {"descargado_en": "2026-11-23T15:20:00Z", "url": "...", "licencia": "CC0 1.0",
     "consulta": "SELECT ...", "respuesta": {"results": {...}}}
"""

import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from radar.contratos.insumos_distritos import NombresWikidata
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

FUENTE = "Wikidata (consulta SPARQL)"
URL = "https://query.wikidata.org/sparql"
LICENCIA = "CC0 1.0"


def consulta(geonameids: Iterable[str]) -> str:
    """Consulta SPARQL de las etiquetas en español de esos GeoNames ID."""
    ids = sorted(set(geonameids))
    if not ids or not all(i.isdigit() for i in ids):
        raise ValueError("se necesitan identificadores numéricos de GeoNames")
    valores = " ".join(f'"{i}"' for i in ids)
    return (
        "SELECT ?item ?gn ?l WHERE { "
        f"VALUES ?gn {{ {valores} }} "
        "?item wdt:P1566 ?gn . "
        '?item rdfs:label ?l . FILTER(LANG(?l) = "es") }'
    )


def _etiquetas(respuesta: Any) -> dict[str, str]:
    try:
        filas = respuesta["results"]["bindings"]
    except (KeyError, TypeError) as error:
        raise FuenteNoDisponible(FUENTE, "respuesta sin resultados SPARQL") from error
    if not isinstance(filas, list):
        raise FuenteNoDisponible(FUENTE, "respuesta sin resultados SPARQL")
    nombres: dict[str, set[str]] = {}
    for fila in filas:
        try:
            geonameid = str(fila["gn"]["value"]).strip()
            etiqueta = str(fila["l"]["value"]).strip()
        except (KeyError, TypeError):
            continue
        if geonameid.isdigit() and etiqueta:
            nombres.setdefault(geonameid, set()).add(etiqueta)
    # Dos elementos con el mismo GeoNames ID y etiquetas distintas: ambiguo, se descarta.
    return {g: e.pop() for g, e in nombres.items() if len(e) == 1}


def interpretar_instantanea(texto: str) -> NombresWikidata:
    """Valida una instantánea guardada (respuesta SPARQL con su fecha)."""
    try:
        datos = json.loads(texto)
        respuesta, fecha = datos["respuesta"], datos["descargado_en"]
    except (ValueError, KeyError, TypeError) as error:
        raise FuenteNoDisponible(FUENTE, "instantánea sin respuesta ni fecha") from error
    try:
        return NombresWikidata(descargado_en=fecha, por_geonameid=_etiquetas(respuesta))
    except ValidationError as error:
        raise FuenteNoDisponible(FUENTE, f"instantánea no válida: {error}") from error


class FuenteWikidataNombres:
    """Consulta en línea; necesita un contacto (URL o correo) para el agente de usuario."""

    def __init__(
        self,
        geonameids: Iterable[str],
        *,
        contacto: str,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not contacto.strip():
            raise ValueError("Wikimedia exige un contacto en el agente de usuario")
        self._consulta = consulta(geonameids)
        self._cabeceras = {
            "Accept": "application/sparql-results+json",
            "User-Agent": f"catalogo-distritos/1.0 ({contacto.strip()})",
        }
        self._cliente = cliente
        self._politica = politica
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "wikidata-en-linea"

    def instantanea(self) -> str:
        """Consulta Wikidata y devuelve la instantánea lista para guardar."""
        texto = descargar_texto(
            FUENTE,
            URL,
            formulario={"query": self._consulta},
            cabeceras=self._cabeceras,
            cliente=self._cliente,
            politica=self._politica,
        )
        try:
            respuesta = json.loads(texto)
        except ValueError as error:
            raise FuenteNoDisponible(FUENTE, "respuesta que no es JSON") from error
        _etiquetas(respuesta)
        envoltorio = {
            "descargado_en": self._ahora().astimezone(UTC).isoformat(),
            "url": URL,
            "licencia": LICENCIA,
            "consulta": self._consulta,
            "respuesta": respuesta,
        }
        return json.dumps(envoltorio, ensure_ascii=False, indent=1) + "\n"

    def obtener(self) -> NombresWikidata:
        return interpretar_instantanea(self.instantanea())


class FuenteWikidataArchivo:
    """Instantánea guardada en el repositorio."""

    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta

    @property
    def id(self) -> str:
        return "wikidata-archivo"

    def obtener(self) -> NombresWikidata:
        try:
            texto = self._ruta.read_text(encoding="utf-8")
        except OSError as error:
            raise FuenteNoDisponible(FUENTE, f"no se pudo leer {self._ruta.name}") from error
        return interpretar_instantanea(texto)
