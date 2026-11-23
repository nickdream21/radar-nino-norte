"""INEI, centros poblados censales por el WFS de su infraestructura de datos espaciales.

La capa ``Interoperabilidad:ig_centropoblado`` del geoservidor del INEI tiene los
94 922 centros poblados de los Censos Nacionales 2017 con su ubicación. Dentro de
cada distrito, el INEI asigna el código de centro poblado ``0001`` a la capital
distrital; así se identifican las capitales.

Respuesta GeoJSON del WFS 1.0.0::

    {"type": "FeatureCollection", "numberMatched": 326, "numberReturned": 326,
     "features": [{"geometry": {"type": "Point", "coordinates": [-79.747, -5.987]},
                   "properties": {"ubigeo": "140308", "codccpp": "0001",
                                  "nombccpp": "OLMOS", ...}}, ...]}

Un filtro mal formado no da un error HTTP sino una página HTML o un informe de
excepción XML con estado 200; ambos se rechazan.
"""

import json
import logging
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from radar.contratos.insumos_distritos import CentroPoblado, ListaCentrosPoblados
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_texto

registro = logging.getLogger(__name__)

FUENTE = "INEI, centros poblados de los Censos Nacionales 2017 (geoservidor IDE INEI)"
BASE = "https://geoespacial.inei.gob.pe/geoserver/Interoperabilidad/ows"
CAPA = "Interoperabilidad:ig_centropoblado"
CODIGO_CAPITAL = "0001"


def url_capitales(ubigeos: Iterable[str]) -> str:
    """Consulta WFS de los centros poblados ``0001`` de los distritos pedidos."""
    lista = sorted(set(ubigeos))
    if not lista or not all(u.isdigit() and len(u) == 6 for u in lista):
        raise ValueError("se necesitan ubigeos de 6 dígitos")
    filtro = f"codccpp='{CODIGO_CAPITAL}' AND ubigeo IN ({','.join(repr(u) for u in lista)})"
    parametros = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": CAPA,
        "outputFormat": "application/json",
        "propertyName": "geom,ubigeo,codccpp,nombccpp",
        "CQL_FILTER": filtro,
    }
    return f"{BASE}?{urlencode(parametros)}"


def _centro(elemento: Any) -> CentroPoblado | None:
    try:
        propiedades = elemento["properties"]
        geometria = elemento["geometry"]
        if not geometria or geometria.get("type") != "Point":
            return None
        longitud, latitud = geometria["coordinates"][:2]
        return CentroPoblado(
            ubigeo=propiedades["ubigeo"],
            codigo=propiedades["codccpp"],
            nombre=(propiedades["nombccpp"] or "").strip(),
            latitud=latitud,
            longitud=longitud,
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


class FuenteIneiCapitales:
    """Ubicación de la capital (centro poblado ``0001``) de cada distrito pedido."""

    def __init__(
        self,
        ubigeos: Iterable[str],
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
    ) -> None:
        self._ubigeos = sorted(set(ubigeos))
        self._cliente = cliente
        self._politica = politica

    @property
    def id(self) -> str:
        return "inei-capitales"

    def obtener(self) -> ListaCentrosPoblados:
        texto = descargar_texto(
            FUENTE, url_capitales(self._ubigeos), cliente=self._cliente, politica=self._politica
        )
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> ListaCentrosPoblados:
        """Valida la respuesta GeoJSON. Separado para probarlo sin red."""
        try:
            datos = json.loads(texto)
            elementos: list[Any] = datos["features"]
        except (ValueError, KeyError, TypeError) as error:
            raise FuenteNoDisponible(
                FUENTE, "respuesta sin la colección GeoJSON esperada"
            ) from error
        if not isinstance(elementos, list):
            raise FuenteNoDisponible(FUENTE, "respuesta sin la colección GeoJSON esperada")
        coincidentes = datos.get("numberMatched")
        if isinstance(coincidentes, int) and coincidentes > len(elementos):
            raise FuenteNoDisponible(
                FUENTE, f"respuesta truncada: {len(elementos)} de {coincidentes} elementos"
            )

        centros: list[CentroPoblado] = []
        for elemento in elementos:
            centro = _centro(elemento)
            if centro is None:
                registro.warning("%s: elemento incompleto descartado: %r", FUENTE, elemento)
                continue
            if centro.codigo != CODIGO_CAPITAL:
                raise FuenteNoDisponible(FUENTE, f"llegó un centro poblado {centro.codigo}")
            centros.append(centro)
        vistos: set[str] = set()
        for centro in centros:
            if centro.ubigeo in vistos:
                raise FuenteNoDisponible(FUENTE, f"dos capitales para el distrito {centro.ubigeo}")
            vistos.add(centro.ubigeo)
        return ListaCentrosPoblados(centros=sorted(centros, key=lambda c: c.ubigeo))
