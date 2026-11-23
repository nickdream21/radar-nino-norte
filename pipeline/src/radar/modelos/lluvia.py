"""M1 v1: probabilidad y nivel de lluvia diaria por distrito a partir de ensambles.

Funciones puras, sin red ni archivos: miembros → conteos → probabilidad por sistema →
mezcla → porcentaje → nivel → tendencia. Los criterios científicos (umbrales, pesos,
reglas de nivel, desfase y representatividad de la celda) viven **solo** aquí y
viajan dentro del producto publicado.

Las probabilidades se calculan con fracciones exactas: así "exactamente el 30 %" no
depende del redondeo de coma flotante. Se redondean una sola vez, sobre la mezcla
final, a enteros de 0 a 100 con la mitad hacia arriba, y el nivel se decide con esos
enteros para que lo publicado sea coherente (nunca "30 % y verde").
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from math import floor
from typing import Literal

from radar.contratos.distritos import Zona
from radar.fuentes.open_meteo_ensambles import Sistema

Nivel = Literal[1, 2, 3, 4]

VERDE: Nivel = 1
AMARILLO: Nivel = 2
NARANJA: Nivel = 3
ROJO: Nivel = 4

UMBRALES_MM: Mapping[Zona, tuple[float, float, float]] = {
    "A": (5.0, 15.0, 40.0),
    "B": (10.0, 30.0, 70.0),
    "C": (10.0, 25.0, 50.0),
    "D": (10.0, 20.0, 40.0),
}
"""T1, T2 y T3 de lluvia diaria (12 a 12 UTC) por zona. Provisionales hasta
contrastarlos con la climatología."""

UMBRALES_CONTEO_MM: tuple[float, ...] = tuple(
    sorted({t for ts in UMBRALES_MM.values() for t in ts})
)
"""Todos los umbrales distintos: los conteos por celda se guardan para cada uno, porque
una misma celda puede representar distritos de zonas distintas."""

PESOS: Mapping[Sistema, Fraction] = {
    Sistema.IFS: Fraction(1, 2),
    Sistema.AIFS: Fraction(1, 4),
    Sistema.GEFS: Fraction(1, 4),
}
ECMWF: frozenset[Sistema] = frozenset({Sistema.IFS, Sistema.AIFS})
"""Sin al menos uno de estos sistemas no se emite pronóstico."""


@dataclass(frozen=True)
class CriteriosNivel:
    """Porcentajes (enteros, comparados con ``>=``) que activan cada nivel."""

    amarillo_t1: int = 30
    naranja_t2: int = 30
    naranja_t3: int = 10
    rojo_t3: int = 30
    rojo_t2: int = 70


CRITERIOS = CriteriosNivel()

DIAS_PRONOSTICO = 7
DIAS_SEMAFORO = 3
"""Días con semáforo propio; los días 4 a 7 se resumen en la tendencia."""
TOPE_TENDENCIA: Nivel = NARANJA

DESFASE_MAXIMO = timedelta(hours=12)
"""Un sistema entra en la mezcla si su corrida está a 12 h o menos de la corrida ECMWF
más reciente (ensamble con desfase; revisado por el meteorólogo)."""

ALTITUD_SIERRA_M = 1000
DIFERENCIA_ALTITUD_COSTA_M = 300
"""Capital por debajo de ``ALTITUD_SIERRA_M``: diferencia máxima con la celda."""
DIFERENCIA_ALTITUD_SIERRA_M = 500
"""Capital a ``ALTITUD_SIERRA_M`` o más: diferencia máxima con la celda."""


# --- Conteos y probabilidades ------------------------------------------------------------


@dataclass(frozen=True)
class Conteo:
    """Miembros válidos de un día y cuántos alcanzan cada umbral de ``UMBRALES_CONTEO_MM``."""

    validos: int
    alcanzan: tuple[int, ...]


def contar(
    lluvia_mm: Sequence[float | None], umbrales: Sequence[float] = UMBRALES_CONTEO_MM
) -> Conteo:
    """Cuenta los miembros válidos que alcanzan o superan cada umbral. ``None`` no cuenta."""
    validos = [v for v in lluvia_mm if v is not None]
    return Conteo(
        validos=len(validos), alcanzan=tuple(sum(v >= u for v in validos) for u in umbrales)
    )


def probabilidad(
    conteo: Conteo, umbral: float, umbrales: Sequence[float] = UMBRALES_CONTEO_MM
) -> Fraction | None:
    """Fracción de miembros válidos que alcanzan ``umbral``; ``None`` sin miembros válidos."""
    if conteo.validos == 0:
        return None
    return Fraction(conteo.alcanzan[list(umbrales).index(umbral)], conteo.validos)


def mezclar(
    por_sistema: Mapping[Sistema, Fraction | None], pesos: Mapping[Sistema, Fraction] = PESOS
) -> Fraction | None:
    """Media ponderada de los sistemas con dato, con los pesos renormalizados.

    ``None`` si no hay ningún sistema de ECMWF con dato: GEFS solo no basta.
    """
    presentes = {s: p for s, p in por_sistema.items() if p is not None}
    if not presentes.keys() & ECMWF:
        return None
    total = sum((pesos[s] for s in presentes), Fraction(0))
    return sum((pesos[s] * p for s, p in presentes.items()), Fraction(0)) / total


def porcentaje(fraccion: Fraction) -> int:
    """Entero de 0 a 100, mitad hacia arriba (no el redondeo bancario de ``round``)."""
    return floor(fraccion * 100 + Fraction(1, 2))


def nivel(p_t1: int, p_t2: int, p_t3: int, criterios: CriteriosNivel = CRITERIOS) -> Nivel:
    """Nivel del día a partir de los porcentajes publicados; gana el más alto."""
    if p_t3 >= criterios.rojo_t3 or p_t2 >= criterios.rojo_t2:
        return ROJO
    if p_t2 >= criterios.naranja_t2 or p_t3 >= criterios.naranja_t3:
        return NARANJA
    if p_t1 >= criterios.amarillo_t1:
        return AMARILLO
    return VERDE


def tendencia(niveles: Sequence[Nivel | None], tope: Nivel = TOPE_TENDENCIA) -> Nivel | None:
    """Nivel más alto de los días dados, con tope; ``None`` si ningún día tiene dato."""
    conocidos = [n for n in niveles if n is not None]
    if not conocidos:
        return None
    alto = max(conocidos)
    return tope if alto > tope else alto


@dataclass(frozen=True)
class DiaDistrito:
    nivel: Nivel | None
    porcentajes: tuple[int, int, int] | None


def dia_distrito(
    conteos: Mapping[Sistema, Conteo | None],
    umbrales_zona: tuple[float, float, float],
    pesos: Mapping[Sistema, Fraction] = PESOS,
    criterios: CriteriosNivel = CRITERIOS,
) -> DiaDistrito:
    """Porcentajes P(≥T1), P(≥T2), P(≥T3) mezclados y nivel de un día de un distrito.

    Sin dato de ECMWF ese día, el día queda sin nivel ni porcentajes.
    """
    porcentajes: list[int] = []
    for umbral in umbrales_zona:
        mezcla = mezclar(
            {s: None if c is None else probabilidad(c, umbral) for s, c in conteos.items()},
            pesos,
        )
        if mezcla is None:
            return DiaDistrito(nivel=None, porcentajes=None)
        porcentajes.append(porcentaje(mezcla))
    p1, p2, p3 = porcentajes
    return DiaDistrito(nivel=nivel(p1, p2, p3, criterios), porcentajes=(p1, p2, p3))


# --- Corridas y celdas -----------------------------------------------------------------


def corrida_ancla(disponibles: Mapping[Sistema, datetime]) -> Sistema | None:
    """Sistema ECMWF con la corrida más reciente (IFS si empatan); fija los días."""
    ecmwf = [s for s in (Sistema.IFS, Sistema.AIFS) if s in disponibles]
    if not ecmwf:
        return None
    return max(ecmwf, key=lambda s: (disponibles[s], s == Sistema.IFS))


def elegir_corridas(
    disponibles: Mapping[Sistema, datetime], desfase: timedelta = DESFASE_MAXIMO
) -> dict[Sistema, datetime] | None:
    """Corridas que entran en la mezcla, o ``None`` si no hay ninguna de ECMWF."""
    ancla = corrida_ancla(disponibles)
    if ancla is None:
        return None
    referencia = disponibles[ancla]
    return {
        s: t
        for s in Sistema
        if (t := disponibles.get(s)) is not None and abs(t - referencia) <= desfase
    }


def pesos_normalizados(
    sistemas: Sequence[Sistema], pesos: Mapping[Sistema, Fraction] = PESOS
) -> dict[Sistema, Fraction]:
    total = sum((pesos[s] for s in sistemas), Fraction(0))
    return {s: pesos[s] / total for s in sistemas}


def mal_representado(altitud_capital_m: float, altitudes_celda_m: Sequence[float | None]) -> bool:
    """La celda no representa bien al distrito: es mar o su altitud difiere demasiado.

    Se mira la celda de cada sistema usado y basta con que una falle. Una altitud
    desconocida no marca nada por sí sola. No se corrige ni se interpola.
    """
    maximo = (
        DIFERENCIA_ALTITUD_COSTA_M
        if altitud_capital_m < ALTITUD_SIERRA_M
        else DIFERENCIA_ALTITUD_SIERRA_M
    )
    for altitud in altitudes_celda_m:
        if altitud is None:
            continue
        if altitud <= 0 or abs(altitud - altitud_capital_m) > maximo:
            return True
    return False
