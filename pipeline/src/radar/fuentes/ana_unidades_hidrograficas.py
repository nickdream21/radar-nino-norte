"""ANA, unidades hidrográficas del Perú (Pfafstetter) por su servicio ArcGIS.

Sirven para decidir la vertiente de cada capital distrital. El primer dígito del
código Pfafstetter (``nivel1``) es la región hidrográfica: ``1`` Pacífico, ``4``
Amazonas (en el norte, toda es cuenca del Marañón, ``498``) y ``0`` Titicaca.

Respuesta ``f=json`` de ArcGIS::

    {"features": [{"attributes": {"codigo": "49898", "nombre": "Cuenca Crisnejas",
                                  "nivel1": "4"},
                   "geometry": {"rings": [[[-78.1, -7.2], ...], ...]}}],
     "exceededTransferLimit": false}

Un error del servidor llega con estado 200 y ``{"error": {...}}``.
"""

import json
import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from radar.contratos.distritos import Vertiente
from radar.contratos.insumos_distritos import (
    ListaUnidadesHidrograficas,
    Punto,
    UnidadHidrografica,
)
from radar.contratos.nino import Caja
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

FUENTE = "ANA, unidades hidrográficas del Perú (GeoSNIRH)"
BASE = (
    "https://geosnirh.ana.gob.pe/server/rest/services/Hosted/"
    "UnidadesHidrograficas/FeatureServer/0/query"
)
VERTIENTES: dict[str, Vertiente] = {"1": "pacifico", "4": "atlantico"}
POR_PAGINA = 100
MAX_PAGINAS = 20
"""Tope de seguridad: la caja del norte tiene menos de 100 unidades."""
SIMPLIFICACION_GRADOS = 0.001
"""Tolerancia de generalización del contorno (~110 m), muy por debajo del margen de duda."""


def url_pagina(caja: Caja, desplazamiento: int) -> str:
    parametros = {
        "where": "1=1",
        "geometry": f"{caja.lon_min},{caja.lat_min},{caja.lon_max},{caja.lat_max}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "codigo,nombre,nivel1",
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": str(SIMPLIFICACION_GRADOS),
        "geometryPrecision": "5",
        "orderByFields": "codigo",
        "resultOffset": str(desplazamiento),
        "resultRecordCount": str(POR_PAGINA),
        "f": "json",
    }
    return f"{BASE}?{urlencode(parametros)}"


def _anillos(geometria: Any) -> list[list[Punto]]:
    anillos: list[list[Punto]] = []
    for anillo in geometria["rings"]:
        puntos = [(float(x), float(y)) for x, y, *_ in anillo]
        if len(puntos) >= 3:
            anillos.append(puntos)
    return anillos


def _unidad(elemento: Any) -> UnidadHidrografica:
    atributos = elemento["attributes"]
    nivel1 = str(atributos["nivel1"]).strip()
    vertiente = VERTIENTES.get(nivel1)
    if vertiente is None:
        raise FuenteNoDisponible(FUENTE, f"región hidrográfica desconocida: {nivel1!r}")
    return UnidadHidrografica(
        codigo=str(atributos["codigo"]).strip(),
        nombre=str(atributos["nombre"]).strip(),
        vertiente=vertiente,
        anillos=_anillos(elemento["geometry"]),
    )


class FuenteAnaUnidadesHidrograficas:
    """Unidades hidrográficas que tocan una caja, con su contorno simplificado."""

    def __init__(
        self,
        caja: Caja,
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
    ) -> None:
        self._caja = caja
        self._cliente = cliente
        self._politica = politica

    @property
    def id(self) -> str:
        return "ana-unidades-hidrograficas"

    def obtener(self) -> ListaUnidadesHidrograficas:
        paginas: list[str] = []
        for numero in range(MAX_PAGINAS):
            texto = descargar_texto(
                FUENTE,
                url_pagina(self._caja, numero * POR_PAGINA),
                cliente=self._cliente,
                politica=self._politica,
            )
            paginas.append(texto)
            if not self._hay_mas(texto):
                return self.interpretar(paginas)
        raise FuenteNoDisponible(FUENTE, f"más de {MAX_PAGINAS} páginas")

    @staticmethod
    def _hay_mas(texto: str) -> bool:
        try:
            return bool(json.loads(texto).get("exceededTransferLimit", False))
        except (ValueError, AttributeError):
            return False

    def interpretar(self, paginas: list[str]) -> ListaUnidadesHidrograficas:
        """Valida las páginas de la consulta. Separado para probarlo sin red."""
        unidades: list[UnidadHidrografica] = []
        for texto in paginas:
            try:
                datos = json.loads(texto)
            except ValueError as error:
                raise FuenteNoDisponible(FUENTE, "respuesta que no es JSON") from error
            if not isinstance(datos, dict):
                raise FuenteNoDisponible(FUENTE, "respuesta sin la lista de elementos")
            if "error" in datos:
                raise FuenteNoDisponible(FUENTE, f"error del servicio: {datos['error']}")
            elementos = datos.get("features")
            if not isinstance(elementos, list):
                raise FuenteNoDisponible(FUENTE, "respuesta sin la lista de elementos")
            for elemento in elementos:
                try:
                    unidades.append(_unidad(elemento))
                except (KeyError, TypeError, ValueError, ValidationError) as error:
                    # Sin contorno o con atributos rotos: no se puede usar para ubicar nada.
                    registro.warning("%s: unidad descartada (%s)", FUENTE, error)
        if not unidades:
            raise FuenteNoDisponible(FUENTE, "ninguna unidad hidrográfica válida")
        codigos = [u.codigo for u in unidades]
        if len(set(codigos)) != len(codigos):
            raise FuenteNoDisponible(FUENTE, "unidades repetidas entre páginas")
        return ListaUnidadesHidrograficas(unidades=unidades)
