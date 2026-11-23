"""Regla de zonas pluviométricas (A, B, C, D) de cada distrito.

La zona solo sirve para elegir los umbrales de lluvia diaria de cada distrito. No
describe cómo le afecta El Niño costero: eso depende de la vertiente (Pacífico o
Atlántico), no de la zona.

La regla es la revisada por el meteorólogo del proyecto y usa solo datos medidos en
la capital distrital. Se evalúa en este orden y gana la primera que se cumple:

1. Vertiente atlántica (cuenca del Marañón): **C** por debajo de
   ``UMBRAL_ATLANTICO_M`` (1500 m) y **D** desde ahí (valles bajos de Jaén y San
   Ignacio frente a la sierra alta de Cajamarca y Huamachuco).
2. **B** si el distrito es de Tumbes ("todo Tumbes").
3. **D** si está en la cuenca del Santa (vertiente del Pacífico), a cualquier altitud.
4. **D** por encima de ``UMBRAL_SIERRA_ALTA_M`` (3000 m).
5. **C** entre 1000 y 3000 m.
6. **A** por debajo de 1000 m si la capital está a menos de ``UMBRAL_LITORAL_KM``
   (20 km) del mar o al sur de ``LATITUD_SUR`` (-6,75°): costa y valles áridos.
7. **B** entre 200 y 1000 m.
8. **B** por debajo de 200 m y a más de ``UMBRAL_INTERIOR_KM`` (60 km) del mar: la
   llanura interior del Alto Piura, Chira medio y Olmos-Motupe.
9. **A** en el resto.

Los cortes (3000 m, 1500 m, 60 km, 20 km, -6,75°) son criterio experto provisional,
pendiente de contraste con percentiles de lluvia de CHIRPS.

Algunos distritos tienen la zona fijada a mano (``ZONAS_FORZADAS``), con su motivo,
cuando el meteorólogo sabe que la capital no representa bien el régimen de lluvia.
La excepción y su motivo quedan siempre en ``revisar``.

La vertiente sale de las unidades hidrográficas oficiales de la ANA en el punto de
la capital, no de la altitud: en Huancabamba, Jaén y San Ignacio la cuenca del
Marañón baja de 1000 m.

Un distrito se marca para revisión cuando un cambio pequeño en sus datos (el error
del modelo de elevación o la posición de la divisoria) le cambiaría la zona, cuando
su zona está forzada o cuando el meteorólogo lo pidió (``REVISION_PENDIENTE``). Los
márgenes están en ``MARGEN_*``.
"""

import math
from dataclasses import dataclass, replace

from radar.contratos.distritos import Vertiente, Zona

UMBRAL_COSTA_M = 200
UMBRAL_SIERRA_M = 1000
UMBRAL_ATLANTICO_M = 1500
"""En la vertiente atlántica separa los valles (C) de la sierra alta (D)."""
UMBRAL_SIERRA_ALTA_M = 3000
UMBRAL_INTERIOR_KM = 60.0
"""Distancia al mar a partir de la cual la llanura baja deja de ser costa (A) y pasa a B."""
UMBRAL_LITORAL_KM = 20.0
"""Por debajo de 1000 m y más cerca del mar que esto, la capital es costa y valles áridos (A)."""
LATITUD_SUR = -6.75
"""Al sur de esta latitud los valles por debajo de 1000 m son áridos (A)."""

DEPARTAMENTO_TUMBES = "24"
CUENCA_SANTA = "Cuenca Santa"
"""Nombre de la unidad hidrográfica del Santa tal como lo da la ANA."""

MARGEN_ALTITUD_M: dict[int, int] = {
    UMBRAL_COSTA_M: 50,
    UMBRAL_SIERRA_M: 100,
    UMBRAL_ATLANTICO_M: 150,
    UMBRAL_SIERRA_ALTA_M: 150,
}
"""Margen de duda alrededor de cada umbral de altitud (error del modelo de elevación).

Solo genera un motivo si mover la altitud dentro del margen cambia la zona: el de
1500 m, por tanto, solo afecta a la vertiente atlántica.
"""
MARGEN_INTERIOR_KM = 10.0
MARGEN_DIVISORIA_KM = 5.0


@dataclass(frozen=True)
class ZonaForzada:
    """Zona fijada a mano para un distrito, con su justificación."""

    zona: Zona
    motivo: str


_LADERA_HUMEDA = (
    "ladera húmeda entre 900 y 1000 m; criterio del meteorólogo con confianza media-baja"
)

ZONAS_FORZADAS: dict[str, ZonaForzada] = {
    "061102": ZonaForzada("C", _LADERA_HUMEDA),  # Bolívar (San Miguel)
    "061106": ZonaForzada("C", _LADERA_HUMEDA),  # La Florida (San Miguel)
    "200305": ZonaForzada("C", _LADERA_HUMEDA),  # Lalaquiz (Huancabamba)
}
"""Excepciones a la regla. Cada una debe justificarse; la lista ha de ser corta."""

REVISION_PENDIENTE: dict[str, str] = {
    "140102": "pendiente de contraste con percentiles",  # Chongoyape
    "240203": "pendiente de contraste con percentiles",  # Canoas de Punta Sal
}
"""Distritos que el meteorólogo pidió revisar aunque la regla no los vea dudosos."""

EJEMPLOS_TABLA: dict[str, Zona] = {
    # A. Costa y valles áridos.
    "200701": "A",  # Pariñas (Talara)
    "200501": "A",  # Paita
    "200801": "A",  # Sechura
    "200101": "A",  # Piura
    "140101": "A",  # Chiclayo
    "130101": "A",  # Trujillo
    # B. Tumbes y piedemonte (todo Tumbes se comprueba aparte).
    "200401": "B",  # Chulucanas
    "200405": "B",  # Morropón
    "200114": "B",  # Tambo Grande (así lo escribe el INEI)
    "200111": "B",  # Las Lomas
    "140308": "B",  # Olmos
    # C. Sierra occidental y valles bajos de la vertiente oriental.
    "200201": "C",  # Ayabaca
    "200202": "C",  # Frías
    "200302": "C",  # Canchaque
    "061301": "C",  # Santa Cruz (provincia de Santa Cruz; no el de Cutervo)
    "060501": "C",  # Contumazá
    "130601": "C",  # Otuzco
    "060801": "C",  # Jaén
    "060901": "C",  # San Ignacio
    # D. Sierra alta.
    "060101": "D",  # Cajamarca
    "060401": "D",  # Chota
    "060601": "D",  # Cutervo
    "130901": "D",  # Huamachuco
    "130809": "D",  # Pataz
}
"""Distritos que la tabla del meteorólogo nombra como ejemplo de cada zona."""


@dataclass(frozen=True)
class DatosZona:
    """Lo que la regla necesita saber de un distrito."""

    ubigeo: str
    altitud_m: int
    vertiente: Vertiente
    cuenca: str
    distancia_costa_km: float
    latitud: float
    """Latitud de la capital, en grados (negativa al sur del ecuador)."""
    distancia_divisoria_km: float = math.inf
    """Solo para decidir si la zona es dudosa; la zona no depende de ella."""


def zona_por_regla(datos: DatosZona) -> Zona:
    """Zona según la regla del módulo, sin aplicar las excepciones."""
    if datos.vertiente == "atlantico":
        return "C" if datos.altitud_m < UMBRAL_ATLANTICO_M else "D"
    if datos.ubigeo.startswith(DEPARTAMENTO_TUMBES):
        return "B"
    if datos.cuenca == CUENCA_SANTA:
        return "D"
    if datos.altitud_m > UMBRAL_SIERRA_ALTA_M:
        return "D"
    if datos.altitud_m >= UMBRAL_SIERRA_M:
        return "C"
    if datos.distancia_costa_km < UMBRAL_LITORAL_KM or datos.latitud < LATITUD_SUR:
        return "A"
    if datos.altitud_m >= UMBRAL_COSTA_M:
        return "B"
    if datos.distancia_costa_km > UMBRAL_INTERIOR_KM:
        return "B"
    return "A"


def zona(datos: DatosZona) -> Zona:
    """Zona del distrito: la forzada si la tiene; si no, la de la regla."""
    forzada = ZONAS_FORZADAS.get(datos.ubigeo)
    return forzada.zona if forzada is not None else zona_por_regla(datos)


def _cambia(datos: DatosZona, variante: DatosZona) -> Zona | None:
    """Zona de ``variante`` si difiere de la de ``datos``."""
    otra = zona(variante)
    return otra if otra != zona(datos) else None


def motivo_divisoria(distancia_km: float, otra: Zona) -> str:
    """Motivo de revisión por cercanía a la divisoria Pacífico-Atlántico."""
    return (
        f"capital a {distancia_km:.1f} km de la divisoria"
        f" Pacífico-Atlántico (en la otra vertiente sería zona {otra})"
    )


def motivos_revision(datos: DatosZona) -> list[str]:
    """Por qué la zona del distrito es fronteriza o discutible; vacía si no lo es."""
    motivos: list[str] = []
    forzada = ZONAS_FORZADAS.get(datos.ubigeo)
    if forzada is not None:
        motivos.append(
            f"zona {forzada.zona} fijada a mano (la regla daría {zona_por_regla(datos)}):"
            f" {forzada.motivo}"
        )
    for umbral, margen in MARGEN_ALTITUD_M.items():
        if abs(datos.altitud_m - umbral) > margen:
            continue
        for altitud in (umbral - margen, umbral + margen):
            otra = _cambia(datos, replace(datos, altitud_m=altitud))
            if otra is not None:
                motivos.append(
                    f"altitud {datos.altitud_m} m, a {margen} m o menos del umbral de"
                    f" {umbral} m (con {altitud} m sería zona {otra})"
                )
                break
    if abs(datos.distancia_costa_km - UMBRAL_INTERIOR_KM) <= MARGEN_INTERIOR_KM:
        for distancia in (
            UMBRAL_INTERIOR_KM - MARGEN_INTERIOR_KM,
            UMBRAL_INTERIOR_KM + MARGEN_INTERIOR_KM,
        ):
            otra = _cambia(datos, replace(datos, distancia_costa_km=distancia))
            if otra is not None:
                motivos.append(
                    f"a {datos.distancia_costa_km:.0f} km del mar, cerca del límite de"
                    f" {UMBRAL_INTERIOR_KM:.0f} km entre costa y llanura interior"
                    f" (con {distancia:.0f} km sería zona {otra})"
                )
                break
    if datos.distancia_divisoria_km <= MARGEN_DIVISORIA_KM:
        opuesta: Vertiente = "pacifico" if datos.vertiente == "atlantico" else "atlantico"
        otra = _cambia(datos, replace(datos, vertiente=opuesta))
        if otra is not None:
            motivos.append(motivo_divisoria(datos.distancia_divisoria_km, otra))
    pendiente = REVISION_PENDIENTE.get(datos.ubigeo)
    if pendiente is not None:
        motivos.append(pendiente)
    return motivos
