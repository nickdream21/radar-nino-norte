"""Estado observado de El Niño: el producto del "termómetro" (``nino/estado.json``).

Cada bloque viene de una fuente distinta, se actualiza a su propio ritmo y lleva
su fecha del dato y su fuente. Un bloque ausente (``null``) significa que su
fuente falló y no había una publicación anterior que conservar.
"""

from itertools import pairwise
from typing import Literal, Self

from pydantic import Field, model_validator

from radar.contratos.base import Contrato, FechaUtc

MAX_SEMANAS = 104
MAX_MESES = 36


class Bloque(Contrato):
    """Campos comunes a todos los bloques del estado de El Niño."""

    fuente: str = Field(min_length=1, description="Origen de los datos, para la atribución.")
    url: str = Field(pattern=r"^https?://", description="Dirección de la fuente.")
    fecha_dato: FechaUtc = Field(description="Fecha del dato más reciente del bloque (UTC).")
    obtenido_en: FechaUtc = Field(
        description=(
            "Momento en que el pipeline leyó la fuente con éxito. Si es anterior a"
            " `generado_en`, el bloque se conservó de una publicación previa."
        )
    )


class ValorSemanal(Contrato):
    """Promedio semanal de temperatura superficial del mar en una región Niño."""

    fecha: FechaUtc = Field(description="Día central de la semana, 00:00 UTC.")
    temperatura: float = Field(ge=-5, le=40, description="Temperatura del mar en °C.")
    anomalia: float = Field(ge=-15, le=15, description="Anomalía respecto a 1991-2020, en °C.")


class IndiceSemanal(Contrato):
    """Último valor y serie reciente de una región Niño."""

    ultimo: ValorSemanal
    serie: list[ValorSemanal] = Field(
        min_length=1,
        max_length=MAX_SEMANAS,
        description="Semanas en orden cronológico; puede tener huecos, nunca valores rellenados.",
    )

    @model_validator(mode="after")
    def _serie_coherente(self) -> Self:
        fechas = [v.fecha for v in self.serie]
        if any(a >= b for a, b in pairwise(fechas)):
            raise ValueError("la serie debe estar en orden cronológico estricto")
        if self.serie[-1] != self.ultimo:
            raise ValueError("el último valor debe coincidir con el final de la serie")
        return self


class BloqueIndicesSemanales(Bloque):
    """Índices semanales Niño 1+2 (costa) y Niño 3.4 (Pacífico central)."""

    nino12: IndiceSemanal
    nino34: IndiceSemanal


class ValorMensual(Contrato):
    """Valor del ICEN para un mes."""

    anio: int = Field(ge=1950, le=2100)
    mes: int = Field(ge=1, le=12)
    fecha: FechaUtc = Field(description="Primer día del mes, 00:00 UTC.")
    valor: float = Field(ge=-10, le=10, description="ICEN en °C.")

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if (self.fecha.year, self.fecha.month) != (self.anio, self.mes):
            raise ValueError("la fecha no corresponde al año y mes")
        return self


class BloqueIcen(Bloque):
    """Índice Costero El Niño (ICEN) del ENFEN, calculado por el IGP.

    Solo el valor numérico: la categoría se añadirá cuando se confirmen los umbrales oficiales.
    """

    ultimo: ValorMensual
    serie: list[ValorMensual] = Field(
        min_length=1,
        max_length=MAX_MESES,
        description="Meses en orden cronológico; puede tener huecos, nunca valores rellenados.",
    )

    @model_validator(mode="after")
    def _serie_coherente(self) -> Self:
        fechas = [v.fecha for v in self.serie]
        if any(a >= b for a, b in pairwise(fechas)):
            raise ValueError("la serie debe estar en orden cronológico estricto")
        if self.serie[-1] != self.ultimo:
            raise ValueError("el último valor debe coincidir con el final de la serie")
        return self


class Caja(Contrato):
    """Rectángulo geográfico en grados decimales."""

    lat_min: float = Field(ge=-90, le=90)
    lat_max: float = Field(ge=-90, le=90)
    lon_min: float = Field(ge=-180, le=180)
    lon_max: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def _ordenada(self) -> Self:
        if self.lat_min >= self.lat_max or self.lon_min >= self.lon_max:
            raise ValueError("los mínimos deben ser menores que los máximos")
        return self


class BloqueMarPaita(Bloque):
    """Anomalía diaria de temperatura del mar frente a Paita (Coral Reef Watch, 5 km)."""

    anomalia: float = Field(
        ge=-15, le=15, description="Promedio de las celdas válidas de la caja, en °C."
    )
    caja: Caja = Field(description="Zona mar adentro promediada.")
    celdas_validas: int = Field(ge=1)
    celdas_totales: int = Field(ge=1)

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if self.celdas_validas > self.celdas_totales:
            raise ValueError("hay más celdas válidas que celdas en total")
        return self


class ComunicadoEnfen(Contrato):
    """Último comunicado oficial del ENFEN, mantenido a mano en ``datos-estaticos/enfen.json``."""

    estado: str = Field(
        min_length=1,
        description='Estado del sistema de alerta, p. ej. "Alerta de El Niño Costero".',
    )
    numero: str = Field(pattern=r"^\d{1,3}-\d{4}$", description='Número del comunicado, "NN-AAAA".')
    fecha: FechaUtc = Field(description="Fecha de emisión del comunicado.")
    enlace: str = Field(pattern=r"^https?://", description="Dónde leer el comunicado.")


class BloqueEnfen(Bloque):
    """Estado del sistema de alerta ENFEN. ``fecha_dato`` es la fecha del comunicado."""

    comunicado: ComunicadoEnfen

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if self.fecha_dato != self.comunicado.fecha:
            raise ValueError("fecha_dato debe ser la fecha del comunicado")
        return self


class EstadoNino(Contrato):
    """Estado observado de El Niño para el termómetro de la web."""

    version_esquema: Literal[1] = 1
    generado_en: FechaUtc
    indices_semanales: BloqueIndicesSemanales | None
    icen: BloqueIcen | None
    mar_paita: BloqueMarPaita | None
    enfen: BloqueEnfen | None

    def bloques(self) -> list[Bloque]:
        """Bloques presentes, en orden fijo."""
        candidatos: list[Bloque | None] = [
            self.indices_semanales,
            self.icen,
            self.mar_paita,
            self.enfen,
        ]
        return [b for b in candidatos if b is not None]
