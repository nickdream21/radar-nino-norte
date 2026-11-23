"""GeoNames, volcado del Perú (``PE.zip``), licencia CC BY 4.0.

Se usa para tres cosas: enlazar cada distrito, provincia y departamento con
Wikidata (de donde salen las tildes), ubicar capitales que el censo 2017 no tiene
(distritos creados después) y contrastar ubicación y altitud de las capitales del
INEI con una fuente independiente.

``PE.txt`` va separado por tabuladores, sin cabecera, con 19 columnas::

    geonameid  name  asciiname  alternatenames  latitude  longitude  feature_class
    feature_code  country_code  cc2  admin1  admin2  admin3  admin4  population
    elevation  dem  timezone  modification_date

En el Perú, ``admin1``, ``admin2`` y ``admin3`` son el ubigeo INEI de departamento
(2 dígitos), provincia (4) y distrito (6). ``dem`` vale ``-9999`` donde el modelo de
elevación no tiene dato.
"""

import io
import logging
import zipfile
from collections.abc import Iterable

import httpx
from pydantic import ValidationError

from radar.contratos.insumos_distritos import ListaLugaresGeonames, LugarGeonames
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_bytes

registro = logging.getLogger(__name__)

FUENTE = "GeoNames (volcado PE)"
URL = "https://download.geonames.org/export/dump/PE.zip"
COLUMNAS = 19
SIN_DATO_DEM = -9999
CLASES_ADMINISTRATIVAS = frozenset({"ADM1", "ADM2", "ADM3"})


def _entero(texto: str) -> int | None:
    texto = texto.strip()
    if not texto:
        return None
    valor = int(texto)
    return None if valor == SIN_DATO_DEM else valor


def _ubigeo(admin1: str, admin2: str, admin3: str, clase: str) -> str | None:
    if clase == "ADM1":
        return admin1 or None
    if clase == "ADM2":
        return admin2 or None
    # Un lugar poblado se asocia a la división más fina que declare.
    return admin3 or admin2 or admin1 or None


class FuenteGeonames:
    """Divisiones administrativas y lugares poblados de los departamentos pedidos."""

    def __init__(
        self,
        departamentos: Iterable[str],
        *,
        cliente: httpx.Client | None = None,
        politica: PoliticaReintentos | None = None,
    ) -> None:
        self._departamentos = frozenset(departamentos)
        self._cliente = cliente
        self._politica = politica

    @property
    def id(self) -> str:
        return "geonames"

    def obtener(self) -> ListaLugaresGeonames:
        contenido = descargar_bytes(FUENTE, URL, cliente=self._cliente, politica=self._politica)
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
                texto = archivo.read("PE.txt").decode("utf-8")
        except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
            raise FuenteNoDisponible(FUENTE, "el ZIP no trae PE.txt legible") from error
        return self.interpretar(texto)

    def interpretar(self, texto: str) -> ListaLugaresGeonames:
        """Filtra las filas de ``PE.txt``. Separado para probarlo sin red."""
        lugares: list[LugarGeonames] = []
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if not linea.strip():
                continue
            campos = linea.split("\t")
            if len(campos) != COLUMNAS:
                registro.warning("%s: línea %d incompleta descartada", FUENTE, numero)
                continue
            clase_rasgo, clase = campos[6], campos[7]
            if clase_rasgo != "P" and clase not in CLASES_ADMINISTRATIVAS:
                continue
            if campos[10] not in self._departamentos:
                continue
            ubigeo = _ubigeo(campos[10], campos[11], campos[12], clase)
            try:
                lugares.append(
                    LugarGeonames(
                        geonameid=campos[0],
                        nombre=campos[1].strip(),
                        latitud=float(campos[4]),
                        longitud=float(campos[5]),
                        clase=clase,
                        ubigeo=ubigeo or "",
                        altitud_m=_entero(campos[15]),
                        altitud_mde_m=_entero(campos[16]),
                    )
                )
            except (ValueError, ValidationError) as error:
                registro.warning("%s: línea %d no válida descartada (%s)", FUENTE, numero, error)
        if not lugares:
            raise FuenteNoDisponible(FUENTE, "ningún lugar de los departamentos pedidos")
        return ListaLugaresGeonames(lugares=lugares)
