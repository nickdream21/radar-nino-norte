"""INEI, Registro Nacional de Municipalidades (RENAMU): lista oficial de distritos.

El RENAMU encuesta cada año a todas las municipalidades provinciales y distritales,
así que su módulo 1 es la lista vigente de distritos con su ubigeo INEI. Se usa el
de 2026 porque incluye Alto Trujillo (Ley 31644, 2022), que aún no figura en las
capas cartográficas del INEI. Publicado en la Plataforma Nacional de Datos Abiertos
con licencia Open Data Commons Attribution (ODC-By).

El ZIP trae un CSV separado por punto y coma, en UTF-8 con BOM, cuyas primeras
columnas son::

    Año;idmunici;ccdd;ccpp;ccdi;Ubigeo;Departamento;Provincia;Distrito;Tipomuni;...

Los nombres vienen en mayúsculas y casi siempre sin tildes.
"""

import csv
import io
import logging
import unicodedata
import zipfile
from collections.abc import Iterable

import httpx
from pydantic import ValidationError

from radar.contratos.insumos_distritos import DistritoOficial, ListaDistritosOficial
from radar.fuentes.base import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_bytes

registro = logging.getLogger(__name__)

FUENTE = "INEI, Registro Nacional de Municipalidades (RENAMU) 2026"
URL = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/CSV/1049-Modulo1963.zip"
PAGINA = (
    "https://www.datosabiertos.gob.pe/dataset/"
    "registro-nacional-de-municipalidades-renamu-2026-instituto-nacional-de-estad%C3%ADstica-e"
)
ANIO = 2026


def _clave(cabecera: str) -> str:
    """Cabecera sin BOM, tildes ni mayúsculas: ``"Año"`` y ``"AÑO"`` dan ``"ano"``."""
    sin_bom = cabecera.lstrip("﻿").strip().lower()
    descompuesta = unicodedata.normalize("NFKD", sin_bom)
    return "".join(c for c in descompuesta if not unicodedata.combining(c))


def _decodificar(contenido: bytes) -> str:
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Ediciones anteriores del RENAMU se publicaron en Windows-1252.
        return contenido.decode("cp1252")


def _leer_zip(contenido: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
            csvs = [n for n in archivo.namelist() if n.lower().endswith(".csv")]
            if len(csvs) != 1:
                raise FuenteNoDisponible(FUENTE, f"se esperaba un CSV en el ZIP y hay {len(csvs)}")
            return _decodificar(archivo.read(csvs[0]))
    except zipfile.BadZipFile as error:
        raise FuenteNoDisponible(FUENTE, "la respuesta no es un ZIP") from error


class FuenteIneiRenamu:
    """Distritos oficiales de los departamentos pedidos."""

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
        return "inei-renamu"

    def obtener(self) -> ListaDistritosOficial:
        contenido = descargar_bytes(FUENTE, URL, cliente=self._cliente, politica=self._politica)
        return self.interpretar_csv(_leer_zip(contenido))

    def interpretar_csv(self, texto: str) -> ListaDistritosOficial:
        """Filtra y valida las filas del CSV. Separado para probarlo sin red."""
        lector = csv.reader(io.StringIO(texto), delimiter=";")
        try:
            cabecera = [_clave(c) for c in next(lector)]
            indice = {
                "anio": cabecera.index("ano"),
                "ubigeo": cabecera.index("ubigeo"),
                "departamento": cabecera.index("departamento"),
                "provincia": cabecera.index("provincia"),
                "distrito": cabecera.index("distrito"),
            }
        except (StopIteration, ValueError) as error:
            raise FuenteNoDisponible(FUENTE, "el CSV no tiene las columnas esperadas") from error

        distritos: list[DistritoOficial] = []
        anios: set[str] = set()
        for numero, fila in enumerate(lector, start=2):
            if not any(c.strip() for c in fila):
                continue
            if len(fila) <= max(indice.values()):
                raise FuenteNoDisponible(FUENTE, f"fila {numero} incompleta")
            valores = {nombre: fila[i].strip() for nombre, i in indice.items()}
            ubigeo = valores["ubigeo"]
            if ubigeo.isdigit() and len(ubigeo) == 5:
                # Una hoja de cálculo intermedia se come el cero inicial ("60101").
                ubigeo = ubigeo.zfill(6)
            if ubigeo[:2] not in self._departamentos:
                continue
            anios.add(valores["anio"])
            try:
                distritos.append(
                    DistritoOficial(
                        ubigeo=ubigeo,
                        departamento=valores["departamento"],
                        provincia=valores["provincia"],
                        nombre=valores["distrito"],
                    )
                )
            except ValidationError as error:
                raise FuenteNoDisponible(FUENTE, f"fila {numero} no válida: {error}") from error

        if anios != {str(ANIO)}:
            raise FuenteNoDisponible(FUENTE, f"se esperaba el año {ANIO} y llegó {sorted(anios)}")
        faltan = self._departamentos - {d.ubigeo[:2] for d in distritos}
        if faltan:
            raise FuenteNoDisponible(
                FUENTE, f"sin distritos para los departamentos {sorted(faltan)}"
            )
        try:
            return ListaDistritosOficial(
                anio=ANIO, distritos=sorted(distritos, key=lambda d: d.ubigeo)
            )
        except ValidationError as error:
            raise FuenteNoDisponible(FUENTE, f"lista no válida: {error}") from error
