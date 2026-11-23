"""Regla de zonas pluviométricas (A, B, C, D) de cada distrito.

La tabla del meteorólogo del proyecto define las zonas por altitud, por vertiente
y con lugares de ejemplo. Esta regla la vuelve reproducible usando solo datos
medidos en la capital distrital, y está ajustada para que todos los ejemplos de
la tabla caigan en su zona. Se evalúa en este orden y gana la primera que se cumple:

1. **D** si la capital drena al Atlántico (cuenca del Marañón), a cualquier altitud.
2. **B** si el distrito es de Tumbes ("todo Tumbes").
3. **D** si está a más de ``UMBRAL_SIERRA_ALTA_M`` (3000 m).
4. **C** si está entre 1000 y 3000 m.
5. **B** si está entre 200 y 1000 m.
6. **B** si está por debajo de 200 m pero a más de ``UMBRAL_INTERIOR_KM`` (60 km) del
   mar: la llanura interior del Alto Piura, Chira medio y Olmos-Motupe.
7. **A** en el resto: por debajo de 200 m y a menos de 60 km del mar.

Decisiones donde la tabla es ambigua:

- **Vertiente.** Sale de las unidades hidrográficas oficiales de la ANA (región
  hidrográfica del Pacífico o del Amazonas) en el punto de la capital, no de la
  altitud: en Huancabamba, Jaén y San Ignacio la cuenca del Marañón baja de 1000 m.
- **Llanura interior por debajo de 200 m.** La tabla pone en B a Tambogrande,
  Chulucanas, Morropón y Olmos, que están por debajo de 200 m, y en A a Piura,
  Chiclayo y Trujillo. Lo que los separa es la distancia al mar: los distritos bajos
  quedan en dos grupos, hasta 50 km (Piura 46 km, Sullana 44 km) y desde 68 km
  (Salas, Lancones, Motupe, Tambogrande 81 km), y 60 km cae en ese hueco.
- **Sierra alta en la vertiente del Pacífico.** La tabla dice "más de 2500 m" para D,
  pero da como ejemplos de C a Ayabaca (2718 m), Contumazá (2660 m) y Otuzco (2642 m),
  y todos sus ejemplos de D drenan al Marañón. Para respetar los ejemplos, en el
  Pacífico se usa 3000 m; los distritos entre 2500 y 3000 m se marcan para revisión
  porque con el texto literal serían D.

Un distrito se marca para revisión cuando un cambio pequeño en sus datos (el error
del modelo de elevación, que la capital no represente a todo el distrito o la
posición de la divisoria) le cambiaría la zona, o cuando cae en la franja en que el
texto y los ejemplos de la tabla no coinciden. Los márgenes están en ``MARGEN_*``.
"""

import math
from dataclasses import dataclass, replace

from radar.contratos.distritos import Vertiente, Zona

UMBRAL_COSTA_M = 200
UMBRAL_SIERRA_M = 1000
UMBRAL_SIERRA_ALTA_M = 3000
UMBRAL_SIERRA_ALTA_TABLA_M = 2500
"""El umbral literal de la tabla, que contradice sus ejemplos de la vertiente del Pacífico."""
UMBRAL_INTERIOR_KM = 60.0
"""Distancia al mar a partir de la cual la llanura baja deja de ser costa árida."""

DEPARTAMENTO_TUMBES = "24"

MARGEN_ALTITUD_M: dict[int, int] = {
    UMBRAL_COSTA_M: 50,
    UMBRAL_SIERRA_M: 100,
    UMBRAL_SIERRA_ALTA_M: 150,
}
"""Margen de duda alrededor de cada umbral de altitud (error del modelo de elevación)."""
MARGEN_INTERIOR_KM = 10.0
MARGEN_DIVISORIA_KM = 5.0

EJEMPLOS_TABLA: dict[str, Zona] = {
    # A. Costa árida.
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
    # C. Sierra occidental.
    "200201": "C",  # Ayabaca
    "200202": "C",  # Frías
    "200302": "C",  # Canchaque
    "061301": "C",  # Santa Cruz (provincia de Santa Cruz; no el de Cutervo)
    "060501": "C",  # Contumazá
    "130601": "C",  # Otuzco
    # D. Sierra alta y vertiente oriental.
    "060101": "D",  # Cajamarca
    "060401": "D",  # Chota
    "060601": "D",  # Cutervo
    "060801": "D",  # Jaén
    "060901": "D",  # San Ignacio
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
    distancia_costa_km: float
    distancia_divisoria_km: float = math.inf
    """Solo para decidir si la zona es dudosa; la zona no depende de ella."""


def zona(datos: DatosZona) -> Zona:
    """Zona pluviométrica según la regla del módulo."""
    if datos.vertiente == "atlantico":
        return "D"
    if datos.ubigeo.startswith(DEPARTAMENTO_TUMBES):
        return "B"
    if datos.altitud_m > UMBRAL_SIERRA_ALTA_M:
        return "D"
    if datos.altitud_m >= UMBRAL_SIERRA_M:
        return "C"
    if datos.altitud_m >= UMBRAL_COSTA_M:
        return "B"
    if datos.distancia_costa_km > UMBRAL_INTERIOR_KM:
        return "B"
    return "A"


def _cambia(datos: DatosZona, variante: DatosZona) -> Zona | None:
    """Zona de ``variante`` si difiere de la de ``datos``."""
    otra = zona(variante)
    return otra if otra != zona(datos) else None


def motivos_revision(datos: DatosZona) -> list[str]:
    """Por qué la zona del distrito es fronteriza o discutible; vacía si no lo es."""
    motivos: list[str] = []
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
    if (
        zona(datos) == "C"
        and datos.vertiente == "pacifico"
        and datos.altitud_m > UMBRAL_SIERRA_ALTA_TABLA_M
    ):
        motivos.append(
            f"altitud {datos.altitud_m} m: con el texto de la tabla (más de"
            f" {UMBRAL_SIERRA_ALTA_TABLA_M} m) sería zona D; es C por los ejemplos de la"
            " tabla (Ayabaca, Contumazá, Otuzco)"
        )
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
            motivos.append(
                f"capital a {datos.distancia_divisoria_km:.1f} km de la divisoria"
                f" Pacífico-Atlántico (en la otra vertiente sería zona {otra})"
            )
    return motivos
