"""Combina las fuentes en el catálogo de distritos. Sin red: recibe todo ya descargado."""

import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from radar.catalogo.geometria import dentro, distancia_a_lineas_km, distancia_km
from radar.catalogo.nombres import clave, con_tildes
from radar.catalogo.zonas import DatosZona, motivos_revision, zona
from radar.contratos.distritos import (
    DEPARTAMENTOS,
    CapitalDistrital,
    CatalogoDistritos,
    Distrito,
    FuenteCatalogo,
    FuenteUbicacion,
)
from radar.contratos.insumos_distritos import (
    CentroPoblado,
    Elevaciones,
    LineaCosta,
    ListaCentrosPoblados,
    ListaDistritosOficial,
    ListaLugaresGeonames,
    ListaUnidadesHidrograficas,
    LugarGeonames,
    NombresWikidata,
    Punto,
    UnidadHidrografica,
)

registro = logging.getLogger(__name__)

CLASES_CABECERA = frozenset({"PPLC", "PPLA", "PPLA2", "PPLA3"})
"""Rasgos de GeoNames que marcan la sede de una división administrativa."""
TOLERANCIA_FUERA_DE_UNIDAD_KM = 2.0
"""Una capital costera puede caer justo fuera del contorno simplificado de su cuenca."""
MOTIVO_FUERA_DE_UNIDAD = "la capital cae fuera de las unidades hidrográficas"
MOTIVO_CAPITAL_GEONAMES = (
    "distrito creado después del censo 2017: la ubicación de la capital es de GeoNames, no del INEI"
)
MOTIVOS_DE_UBICACION = (MOTIVO_FUERA_DE_UNIDAD, MOTIVO_CAPITAL_GEONAMES)
"""Comienzo de los motivos de revisión que no salen de la regla de zonas, sino de cómo se
ubicó la capital. Se conservan al recalcular las zonas sin volver a descargar."""


class CatalogoIncompleto(Exception):
    """Falta un dato imprescindible de algún distrito; no se completa con suposiciones."""


@dataclass(frozen=True)
class Insumos:
    """Todo lo que el catálogo necesita, ya validado por los adaptadores."""

    oficial: ListaDistritosOficial
    capitales_inei: ListaCentrosPoblados
    geonames: ListaLugaresGeonames
    nombres_wikidata: NombresWikidata
    unidades: ListaUnidadesHidrograficas
    costa: LineaCosta
    fuentes: Sequence[FuenteCatalogo]


@dataclass
class Informe:
    """Lo que conviene revisar a mano después de generar el catálogo."""

    nombres_sin_confirmar: list[str] = field(default_factory=list)
    tildes_en_desacuerdo: list[str] = field(default_factory=list)
    capitales_sin_censo: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Ubicacion:
    nombre_inei: str
    punto: Punto
    fuente: FuenteUbicacion
    lugares: list[LugarGeonames]


def indices_geonames(
    geonames: ListaLugaresGeonames,
) -> tuple[dict[str, LugarGeonames], dict[str, list[LugarGeonames]]]:
    administrativos: dict[str, LugarGeonames] = {}
    poblados: dict[str, list[LugarGeonames]] = defaultdict(list)
    for lugar in geonames.lugares:
        if lugar.clase.startswith("ADM"):
            administrativos.setdefault(lugar.ubigeo, lugar)
        else:
            poblados[lugar.ubigeo].append(lugar)
    return administrativos, poblados


def lugares_con_nombre(
    nombre_inei: str, ubigeo: str, poblados: dict[str, list[LugarGeonames]]
) -> list[LugarGeonames]:
    """Lugares poblados de GeoNames con ese nombre en la provincia del distrito.

    Se busca en toda la provincia porque GeoNames asigna los lugares a los distritos
    vigentes cuando los registró: Alto Trujillo (2022) figura aún en El Porvenir.
    """
    objetivo = clave(nombre_inei)
    return [
        lugar
        for codigo, lugares in poblados.items()
        if codigo.startswith(ubigeo[:4])
        for lugar in lugares
        if clave(lugar.nombre) == objetivo
    ]


def cabecera_geonames(
    ubigeo: str, nombre_capital_inei: str, poblados: dict[str, list[LugarGeonames]]
) -> LugarGeonames | None:
    """La sede del distrito según GeoNames, para contrastar con el INEI."""
    sedes = [p for p in poblados.get(ubigeo, []) if p.clase in CLASES_CABECERA]
    if len(sedes) == 1:
        return sedes[0]
    mismas = [p for p in sedes if clave(p.nombre) == clave(nombre_capital_inei)]
    return mismas[0] if len(mismas) == 1 else None


def _ubicacion(
    ubigeo: str,
    nombre_distrito_inei: str,
    capitales: dict[str, CentroPoblado],
    poblados: dict[str, list[LugarGeonames]],
) -> _Ubicacion:
    centro = capitales.get(ubigeo)
    if centro is not None:
        return _Ubicacion(
            nombre_inei=centro.nombre,
            punto=(centro.longitud, centro.latitud),
            fuente="inei-ccpp",
            lugares=lugares_con_nombre(centro.nombre, ubigeo, poblados),
        )
    # Distrito creado después del censo 2017: su ley fija como capital el núcleo
    # urbano del mismo nombre. Se ubica con GeoNames solo si hay uno y solo uno.
    lugares = lugares_con_nombre(nombre_distrito_inei, ubigeo, poblados)
    if len(lugares) != 1:
        raise CatalogoIncompleto(
            f"{ubigeo} {nombre_distrito_inei}: sin capital en el censo y {len(lugares)}"
            " lugares homónimos en GeoNames"
        )
    lugar = lugares[0]
    return _Ubicacion(
        nombre_inei=nombre_distrito_inei,
        punto=(lugar.longitud, lugar.latitud),
        fuente="geonames",
        lugares=lugares,
    )


def _unidad_de(
    punto: Punto, unidades: Sequence[UnidadHidrografica]
) -> tuple[UnidadHidrografica, float]:
    """Unidad que contiene el punto (distancia 0) o, si ninguna, la más cercana."""
    for unidad in unidades:
        if dentro(punto, unidad.anillos):
            return unidad, 0.0
    cercanas = [(distancia_a_lineas_km(punto, u.anillos), u) for u in unidades]
    distancia, unidad = min(cercanas, key=lambda par: par[0])
    return unidad, distancia


def construir_catalogo(
    insumos: Insumos,
    altitudes: Callable[[list[Punto]], Elevaciones],
    ahora: datetime,
) -> tuple[CatalogoDistritos, Informe]:
    """Arma y valida el catálogo; lanza ``CatalogoIncompleto`` si falta algún dato."""
    informe = Informe()
    administrativos, poblados = indices_geonames(insumos.geonames)
    wikidata = insumos.nombres_wikidata.por_geonameid
    capitales = {c.ubigeo: c for c in insumos.capitales_inei.centros}

    def candidatos(lugares: Sequence[LugarGeonames]) -> list[str]:
        etiquetas = [wikidata[lugar.geonameid] for lugar in lugares if lugar.geonameid in wikidata]
        return etiquetas + [lugar.nombre for lugar in lugares]

    def nombre(inei: str, lugares: Sequence[LugarGeonames], que: str) -> str:
        ortografia = con_tildes(inei, candidatos(lugares))
        if not ortografia.confirmado:
            informe.nombres_sin_confirmar.append(f"{que}: {ortografia.nombre}")
        if ortografia.descartadas:
            informe.tildes_en_desacuerdo.append(
                f"{que}: {ortografia.nombre} (también {', '.join(ortografia.descartadas)})"
            )
        return ortografia.nombre

    oficiales = insumos.oficial.distritos
    ubicaciones = [_ubicacion(d.ubigeo, d.nombre, capitales, poblados) for d in oficiales]
    metros = altitudes([u.punto for u in ubicaciones]).metros
    if len(metros) != len(ubicaciones):
        raise CatalogoIncompleto("no llegó la altitud de todas las capitales")

    # Distrito y capital homónimos son el mismo topónimo: comparten candidatos.
    nombres_distrito: dict[str, str] = {}
    nombres_capital: dict[str, str] = {}
    for oficial, ubicacion in zip(oficiales, ubicaciones, strict=True):
        ubigeo = oficial.ubigeo
        adm3 = [administrativos[ubigeo]] if ubigeo in administrativos else []
        homonimos = clave(oficial.nombre) == clave(ubicacion.nombre_inei)
        lugares_distrito = adm3 + (ubicacion.lugares if homonimos else [])
        nombres_distrito[ubigeo] = nombre(oficial.nombre, lugares_distrito, f"distrito {ubigeo}")
        nombres_capital[ubigeo] = nombre(
            ubicacion.nombre_inei,
            ubicacion.lugares + (adm3 if homonimos else []),
            f"capital {ubigeo}",
        )
    provincias: dict[str, str] = {}
    for oficial in oficiales:
        codigo = oficial.ubigeo[:4]
        if codigo in provincias:
            continue
        adm2 = [administrativos[codigo]] if codigo in administrativos else []
        extra: list[str] = []
        # La provincia suele llamarse como su distrito capital (código terminado en 01).
        if clave(nombres_distrito.get(codigo + "01", "")) == clave(oficial.provincia):
            extra = [nombres_distrito[codigo + "01"]]
        ortografia = con_tildes(oficial.provincia, candidatos(adm2) + extra)
        if not ortografia.confirmado:
            informe.nombres_sin_confirmar.append(f"provincia {codigo}: {ortografia.nombre}")
        provincias[codigo] = ortografia.nombre

    unidades = insumos.unidades.unidades
    por_vertiente = {
        v: [anillo for u in unidades if u.vertiente == v for anillo in u.anillos]
        for v in ("pacifico", "atlantico")
    }
    distritos: list[Distrito] = []
    for oficial, ubicacion, altitud in zip(oficiales, ubicaciones, metros, strict=True):
        ubigeo = oficial.ubigeo
        departamento = DEPARTAMENTOS[ubigeo[:2]]
        if clave(departamento) != clave(oficial.departamento):
            raise CatalogoIncompleto(f"{ubigeo}: departamento {oficial.departamento!r} inesperado")
        nombre_distrito = nombres_distrito[ubigeo]
        nombre_capital = nombres_capital[ubigeo]

        unidad, fuera_km = _unidad_de(ubicacion.punto, unidades)
        opuesta = "atlantico" if unidad.vertiente == "pacifico" else "pacifico"
        datos = DatosZona(
            ubigeo=ubigeo,
            altitud_m=round(altitud),
            vertiente=unidad.vertiente,
            cuenca=unidad.nombre,
            # Redondeada como se guarda, igual que la distancia a la costa.
            latitud=round(ubicacion.punto[1], 5),
            # Redondeada como se guarda, para que la regla dé lo mismo al releer el archivo.
            distancia_costa_km=round(
                distancia_a_lineas_km(ubicacion.punto, insumos.costa.tramos), 1
            ),
            distancia_divisoria_km=distancia_a_lineas_km(ubicacion.punto, por_vertiente[opuesta]),
        )
        revisar = motivos_revision(datos)
        if fuera_km > TOLERANCIA_FUERA_DE_UNIDAD_KM:
            revisar.append(
                f"{MOTIVO_FUERA_DE_UNIDAD}; se usó la más cercana ({unidad.nombre}, a"
                f" {fuera_km:.1f} km)"
            )
        if ubicacion.fuente == "geonames":
            informe.capitales_sin_censo.append(f"{ubigeo} {nombre_distrito}")
            revisar.append(MOTIVO_CAPITAL_GEONAMES)
        distritos.append(
            Distrito(
                ubigeo=ubigeo,
                nombre=nombre_distrito,
                provincia=provincias[ubigeo[:4]],
                departamento=departamento,
                capital=CapitalDistrital(
                    nombre=nombre_capital,
                    latitud=round(ubicacion.punto[1], 5),
                    longitud=round(ubicacion.punto[0], 5),
                    altitud_m=datos.altitud_m,
                    fuente_ubicacion=ubicacion.fuente,
                ),
                vertiente=datos.vertiente,
                cuenca=unidad.nombre,
                distancia_costa_km=datos.distancia_costa_km,
                zona=zona(datos),
                revisar=revisar,
            )
        )
    catalogo = CatalogoDistritos(
        generado_en=ahora, fuentes=list(insumos.fuentes), distritos=distritos
    )
    return catalogo, informe


@dataclass(frozen=True)
class Comparacion:
    """Diferencia entre la capital del catálogo y la sede del distrito en GeoNames."""

    ubigeo: str
    distrito: str
    zona: str
    nombre_geonames: str
    distancia_km: float
    altitud_catalogo_m: int
    altitud_geonames_m: int | None


def comparar_con_geonames(
    catalogo: CatalogoDistritos, geonames: ListaLugaresGeonames
) -> list[Comparacion]:
    """Contrasta posición y altitud de cada capital con la sede que da GeoNames."""
    _, poblados = indices_geonames(geonames)
    comparaciones: list[Comparacion] = []
    for distrito in catalogo.distritos:
        sede = cabecera_geonames(distrito.ubigeo, clave(distrito.capital.nombre), poblados)
        if sede is None:
            continue
        capital = distrito.capital
        comparaciones.append(
            Comparacion(
                ubigeo=distrito.ubigeo,
                distrito=distrito.nombre,
                zona=distrito.zona,
                nombre_geonames=sede.nombre,
                distancia_km=distancia_km(
                    (capital.longitud, capital.latitud), (sede.longitud, sede.latitud)
                ),
                altitud_catalogo_m=capital.altitud_m,
                altitud_geonames_m=sede.altitud_m
                if sede.altitud_m is not None
                else sede.altitud_mde_m,
            )
        )
    return comparaciones
