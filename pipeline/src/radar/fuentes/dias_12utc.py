"""Lluvia acumulada por día pluviométrico de 12 UTC a 12 UTC (7 a. m. a 7 a. m. en Perú).

En el norte del Perú la convección es de tarde y noche; un corte a medianoche UTC
(19 h locales) partiría los eventos en dos. Por eso el día ``D`` va de ``D 12:00 UTC``
(incluido) a ``D+1 12:00 UTC`` (excluido).

Cada valor de la serie es la lluvia caída en el intervalo que **termina** en su hora,
``(t_anterior, t]``, como entrega Open-Meteo. Así, con pasos de 1 hora el día ``D``
suma las horas etiquetadas de ``D 13:00`` a ``D+1 12:00``; con pasos de 3 horas, de
``D 15:00`` a ``D+1 12:00``; con pasos de 6 horas, de ``D 18:00`` a ``D+1 12:00``.

Reglas:

- El primer valor de la serie no tiene intervalo conocido (no se sabe cuándo empezó) y
  no se usa.
- Un día solo se entrega si sus intervalos cubren las 24 horas completas. Un día parcial
  se omite; nunca se escala.
- Si un intervalo cruza las 12 UTC no hay forma exacta de repartirlo: se lanza
  ``CorteInexacto`` en lugar de aproximar.
- Un valor ausente o inválido (``None``, NaN, infinito o un centinela negativo como
  ``-99.99``) invalida el día entero: el día aparece con ``None``, nunca con una suma
  parcial.
- Los negativos pequeños (hasta ``-TOLERANCIA_NEGATIVA``) sí son datos: Open-Meteo
  obtiene la lluvia de cada paso restando acumulados y deja ``-0.1`` sueltos en días
  secos. Se suman tal cual, porque la suma de las diferencias de un día reproduce el
  acumulado del modelo; solo el total del día se lleva a 0 si queda negativo.
"""

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

HORA_CORTE = 12
"""Hora UTC en que empieza y termina el día pluviométrico."""
UN_DIA = timedelta(days=1)
TOLERANCIA_NEGATIVA = 0.5
"""mm. Un paso más negativo que esto no es ruido de desacumulación: es un dato inválido."""


class CorteInexacto(ValueError):
    """La serie no permite formar días de 12 a 12 UTC sin repartir un intervalo."""


def inicio_dia(instante: datetime) -> datetime:
    """Inicio (12 UTC) del día pluviométrico que contiene ``instante``."""
    utc = instante.astimezone(UTC)
    corte = utc.replace(hour=HORA_CORTE, minute=0, second=0, microsecond=0)
    return corte if utc >= corte else corte - UN_DIA


def primer_inicio_desde(instante: datetime) -> datetime:
    """Primer inicio de día (12 UTC) igual o posterior a ``instante``."""
    inicio = inicio_dia(instante)
    return inicio if inicio == instante.astimezone(UTC) else inicio + UN_DIA


def _valido(valor: float | None) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    numero = float(valor)
    if not math.isfinite(numero) or numero < -TOLERANCIA_NEGATIVA:
        return None
    return numero


def acumular_dias_12utc(
    fines: Sequence[datetime], valores: Sequence[float | None]
) -> dict[datetime, float | None]:
    """Suma ``valores`` por día de 12 a 12 UTC.

    ``fines`` son las horas en que termina cada intervalo, con zona horaria y en orden
    estrictamente creciente. Devuelve ``{inicio del día: lluvia en mm o None}`` solo con
    los días completos, en orden. ``None`` indica que algún intervalo del día no tenía
    un valor válido.
    """
    if len(fines) != len(valores):
        raise ValueError("fines y valores tienen distinta longitud")
    if any(fin.tzinfo is None for fin in fines):
        raise ValueError("todas las horas deben tener zona horaria")

    # Por día: hasta qué hora está cubierto desde su inicio, la suma y si hubo un valor
    # inválido. Los intervalos son contiguos, así que basta con que el primero del día
    # empiece a las 12 UTC y el último termine a las 12 UTC siguientes.
    cubierto: dict[datetime, datetime] = {}
    sumas: dict[datetime, float] = {}
    invalidos: set[datetime] = set()
    for i in range(1, len(fines)):
        desde, hasta = fines[i - 1].astimezone(UTC), fines[i].astimezone(UTC)
        if hasta <= desde:
            raise ValueError(f"horas no crecientes en {hasta.isoformat()}")
        dia = inicio_dia(desde)
        if hasta > dia + UN_DIA:
            raise CorteInexacto(
                f"el intervalo {desde.isoformat()} a {hasta.isoformat()} cruza las 12 UTC"
            )
        if dia not in cubierto:
            if desde != dia:
                continue  # día empezado antes de la serie: parcial
            sumas[dia] = 0.0
        cubierto[dia] = hasta
        valor = _valido(valores[i])
        if valor is None:
            invalidos.add(dia)
        else:
            sumas[dia] += valor

    return {
        dia: (None if dia in invalidos else max(0.0, round(sumas[dia], 2)))
        for dia, hasta in cubierto.items()
        if hasta == dia + UN_DIA
    }
