"""Regenera ``datos-estaticos/distritos.json`` desde las fuentes (``radar generar-distritos``).

No forma parte de la ingesta horaria: se ejecuta a mano cuando cambia la lista
oficial de distritos o la regla de zonas, y el resultado se revisa y se confirma.
Gasta unas 330 unidades de la cuota diaria de Open-Meteo (una por capital).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from radar.catalogo.construir import (
    Comparacion,
    Informe,
    Insumos,
    comparar_con_geonames,
    construir_catalogo,
    indices_geonames,
    lugares_con_nombre,
)
from radar.contratos.distritos import DEPARTAMENTOS, CatalogoDistritos, FuenteCatalogo
from radar.contratos.insumos_distritos import (
    Elevaciones,
    ListaCentrosPoblados,
    ListaDistritosOficial,
    ListaLugaresGeonames,
    Punto,
)
from radar.contratos.nino import Caja
from radar.fuentes import (
    FuenteDatos,
    ana_unidades_hidrograficas,
    geonames,
    inei_centros_poblados,
    inei_renamu,
    natural_earth,
    open_meteo_elevacion,
    wikidata,
)
from radar.fuentes.ana_unidades_hidrograficas import FuenteAnaUnidadesHidrograficas
from radar.fuentes.geonames import FuenteGeonames
from radar.fuentes.http import PoliticaReintentos
from radar.fuentes.inei_centros_poblados import FuenteIneiCapitales
from radar.fuentes.inei_renamu import FuenteIneiRenamu
from radar.fuentes.natural_earth import FuenteNaturalEarthCosta
from radar.fuentes.open_meteo_elevacion import FuenteOpenMeteoElevacion
from radar.fuentes.wikidata import FuenteWikidataArchivo, FuenteWikidataNombres
from radar.publicacion.escritor import escribir_json

registro = logging.getLogger(__name__)

CAJA_REGION = Caja(lat_min=-10.0, lat_max=-3.0, lon_min=-82.0, lon_max=-76.0)
"""Caja de trabajo para cuencas y costa; contiene holgadamente las cinco regiones."""


def _atribucion(
    campos: str, nombre: str, url: str, licencia: str, atribucion: str, en: datetime
) -> FuenteCatalogo:
    return FuenteCatalogo(
        campos=campos,
        nombre=nombre,
        url=url,
        licencia=licencia,
        atribucion=atribucion,
        descargado_en=en,
    )


def geonameids_para_wikidata(
    oficial: ListaDistritosOficial, capitales: ListaCentrosPoblados, lugares: ListaLugaresGeonames
) -> set[str]:
    """Provincias, distritos y lugares homónimos de cada capital: los que necesitan tildes."""
    _, poblados = indices_geonames(lugares)
    ids = {lug.geonameid for lug in lugares.lugares if lug.clase in ("ADM2", "ADM3")}
    nombres = {c.ubigeo: c.nombre for c in capitales.centros}
    for distrito in oficial.distritos:
        nombre = nombres.get(distrito.ubigeo, distrito.nombre)
        ids.update(lug.geonameid for lug in lugares_con_nombre(nombre, distrito.ubigeo, poblados))
    return ids


def generar(
    instantanea_wikidata: Path,
    *,
    contacto_wikidata: str | None = None,
    ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    cliente: httpx.Client | None = None,
    politica: PoliticaReintentos | None = None,
) -> tuple[CatalogoDistritos, Informe, ListaLugaresGeonames]:
    """Descarga todas las fuentes y arma el catálogo.

    Las tildes salen de la instantánea de Wikidata guardada en el repositorio; con
    ``contacto_wikidata`` se renueva antes en línea (y se sobrescribe el archivo).
    """

    def leer[T](fuente: FuenteDatos[T]) -> tuple[T, datetime]:
        registro.info("Leyendo %s", fuente.id)
        return fuente.obtener(), ahora()

    oficial, t_renamu = leer(FuenteIneiRenamu(DEPARTAMENTOS, cliente=cliente, politica=politica))
    capitales, t_inei = leer(
        FuenteIneiCapitales(
            (d.ubigeo for d in oficial.distritos), cliente=cliente, politica=politica
        )
    )
    lugares, t_geonames = leer(FuenteGeonames(DEPARTAMENTOS, cliente=cliente, politica=politica))
    if contacto_wikidata:
        en_linea = FuenteWikidataNombres(
            geonameids_para_wikidata(oficial, capitales, lugares),
            contacto=contacto_wikidata,
            cliente=cliente,
            politica=politica,
        )
        escribir_texto(en_linea.instantanea(), instantanea_wikidata)
    nombres, _ = leer(FuenteWikidataArchivo(instantanea_wikidata))
    t_wikidata = nombres.descargado_en
    unidades, t_ana = leer(
        FuenteAnaUnidadesHidrograficas(CAJA_REGION, cliente=cliente, politica=politica)
    )
    costa, t_costa = leer(FuenteNaturalEarthCosta(CAJA_REGION, cliente=cliente, politica=politica))

    momentos: dict[str, datetime] = {}

    def altitudes(puntos: list[Punto]) -> Elevaciones:
        resultado, momentos["elevacion"] = leer(
            FuenteOpenMeteoElevacion(puntos, cliente=cliente, politica=politica)
        )
        return resultado

    fuentes_parciales = [
        _atribucion(
            "ubigeo, nombre, provincia, departamento",
            inei_renamu.FUENTE,
            inei_renamu.PAGINA,
            "Open Data Commons Attribution License (ODC-By) 1.0",
            "Instituto Nacional de Estadística e Informática (INEI), RENAMU 2026",
            t_renamu,
        ),
        _atribucion(
            "capital.nombre, capital.latitud, capital.longitud",
            inei_centros_poblados.FUENTE,
            inei_centros_poblados.BASE,
            "Información pública del Estado peruano, de acceso libre y gratuito"
            " (sin restricciones de acceso declaradas en el servicio)",
            "Instituto Nacional de Estadística e Informática (INEI), Censos Nacionales 2017",
            t_inei,
        ),
        _atribucion(
            "tildes de los nombres (solo si coinciden letra por letra con el INEI)",
            wikidata.FUENTE,
            wikidata.URL,
            "CC0 1.0",
            "Wikidata",
            t_wikidata,
        ),
        _atribucion(
            "enlace INEI-Wikidata, capitales posteriores al censo 2017, contraste",
            geonames.FUENTE,
            geonames.URL,
            "CC BY 4.0",
            "GeoNames (www.geonames.org)",
            t_geonames,
        ),
        _atribucion(
            "vertiente, cuenca",
            ana_unidades_hidrograficas.FUENTE,
            ana_unidades_hidrograficas.BASE,
            "Información pública del Estado peruano; solo se guarda el nombre de la"
            " unidad y su región hidrográfica, no su geometría",
            "Autoridad Nacional del Agua (ANA), Sistema Nacional de Información de"
            " Recursos Hídricos",
            t_ana,
        ),
        _atribucion(
            "distancia_costa_km",
            natural_earth.FUENTE,
            natural_earth.URL,
            "Dominio público",
            "Made with Natural Earth",
            t_costa,
        ),
    ]
    # La altitud se pide al construir (necesita las ubicaciones); su atribución se
    # añade al final con la hora real de la descarga.
    insumos = Insumos(
        oficial=oficial,
        capitales_inei=capitales,
        geonames=lugares,
        nombres_wikidata=nombres,
        unidades=unidades,
        costa=costa,
        fuentes=fuentes_parciales,
    )
    catalogo, informe = construir_catalogo(insumos, altitudes, ahora())
    elevacion = _atribucion(
        "capital.altitud_m",
        open_meteo_elevacion.FUENTE,
        open_meteo_elevacion.BASE,
        "Copernicus DEM GLO-90: licencia gratuita de Copernicus con redistribución"
        " permitida; servicio Open-Meteo, datos CC BY 4.0",
        "Copernicus DEM GLO-90 © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH"
        " 2014-2018, provisto en el marco de COPERNICUS por la Unión Europea y la ESA;"
        " altitud servida por Open-Meteo.com",
        momentos["elevacion"],
    )
    catalogo = catalogo.model_copy(update={"fuentes": [*catalogo.fuentes, elevacion]})
    return CatalogoDistritos.model_validate(catalogo.model_dump()), informe, lugares


def escribir_texto(texto: str, destino: Path) -> None:
    """Escritura atómica de un texto (la instantánea de Wikidata)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8", newline="\n")
    temporal.replace(destino)


def generar_archivo(
    destino: Path,
    instantanea_wikidata: Path,
    *,
    contacto_wikidata: str | None = None,
    ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    cliente: httpx.Client | None = None,
    politica: PoliticaReintentos | None = None,
) -> tuple[CatalogoDistritos, Informe, list[Comparacion]]:
    """Genera el catálogo, lo escribe en ``destino`` y devuelve el informe y el contraste."""
    catalogo, informe, lugares = generar(
        instantanea_wikidata,
        contacto_wikidata=contacto_wikidata,
        ahora=ahora,
        cliente=cliente,
        politica=politica,
    )
    escribir_json(catalogo, destino)
    return catalogo, informe, comparar_con_geonames(catalogo, lugares)
