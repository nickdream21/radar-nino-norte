"""Lluvia por distrito (M1 v1): producto ``lluvia/distritos.json`` y archivo de corridas.

El producto da, para cada distrito, el nivel (1 verde, 2 amarillo, 3 naranja, 4 rojo)
y las probabilidades de alcanzar los umbrales T1, T2 y T3 de su zona en los tres
primeros días pluviométricos (12 a 12 UTC), más una tendencia para los días 4 a 7.
No lleva textos para el público y declara que aún no está verificado.

``ArchivoLluvia`` es el formato del archivo de pronósticos emitidos (ADR 0006): los
valores por miembro y los conteos que permiten rehacer las probabilidades sin el
código del pipeline. Se documenta en ``docs/archivo-pronosticos.md``.
"""

from datetime import timedelta
from itertools import pairwise
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from radar.contratos.base import Contrato, FechaUtc
from radar.contratos.distritos import Zona

SistemaEnsamble = Literal["ecmwf_ifs", "ecmwf_aifs", "ncep_gefs"]
"""ECMWF IFS ENS, ECMWF AIFS ENS y NCEP GEFS, todos a 0.25°."""

NivelLluvia = Literal[1, 2, 3, 4]
"""1 verde, 2 amarillo, 3 naranja, 4 rojo."""

Porcentaje = Annotated[int, Field(ge=0, le=100)]


# --- Producto publicado ------------------------------------------------------------------


class UmbralesZona(Contrato):
    t1_mm: float = Field(gt=0)
    t2_mm: float = Field(gt=0)
    t3_mm: float = Field(gt=0)

    @model_validator(mode="after")
    def _crecientes(self) -> Self:
        if not self.t1_mm < self.t2_mm < self.t3_mm:
            raise ValueError("los umbrales deben ser crecientes")
        return self


class CriteriosNiveles(Contrato):
    """Porcentajes mínimos (comparados con ``>=``) que activan cada nivel; gana el más alto."""

    amarillo_t1: Porcentaje
    naranja_t2: Porcentaje
    naranja_t3: Porcentaje
    rojo_t3: Porcentaje
    rojo_t2: Porcentaje


class MetodoLluvia(Contrato):
    """Criterios con que se calculó el producto, para que viajen con los datos."""

    modelo: Literal["m1-v1"]
    pesos: dict[SistemaEnsamble, float] = Field(description="Pesos nominales de la mezcla.")
    umbrales_mm: dict[Zona, UmbralesZona] = Field(
        description="Lluvia diaria de 12 a 12 UTC; provisionales hasta contrastarlos."
    )
    niveles: CriteriosNiveles
    tope_tendencia: NivelLluvia
    desfase_maximo_h: int = Field(
        ge=0, description="Distancia máxima entre la corrida de un sistema y la ECMWF más reciente."
    )
    altitud_sierra_m: int
    diferencia_altitud_costa_m: int = Field(
        description="Capital por debajo de altitud_sierra_m: diferencia máxima con la celda."
    )
    diferencia_altitud_sierra_m: int = Field(
        description="Capital a altitud_sierra_m o más: diferencia máxima con la celda."
    )


class CorridaUsada(Contrato):
    sistema: SistemaEnsamble
    modelo: str = Field(description="Identificador del modelo en Open-Meteo.")
    inicializacion: FechaUtc
    miembros: int = Field(ge=1)
    peso: float = Field(gt=0, le=1, description="Peso renormalizado entre las corridas usadas.")


class DiaPronostico(Contrato):
    """Día pluviométrico: de las 7 a. m. a las 7 a. m. del día siguiente en Perú."""

    inicio: FechaUtc
    fin: FechaUtc
    sistemas: list[SistemaEnsamble] = Field(description="Sistemas con dato ese día.")

    @model_validator(mode="after")
    def _un_dia(self) -> Self:
        if self.fin - self.inicio != timedelta(days=1):
            raise ValueError("un día dura 24 horas")
        return self


class PeriodoTendencia(Contrato):
    """Días 4 a 7: un único nivel, el más alto, con tope y confianza baja."""

    inicio: FechaUtc
    fin: FechaUtc
    confianza: Literal["baja"]


class CeldaModelo(Contrato):
    """Celda de 0.25° que Open-Meteo usó para el distrito (la del sistema ECMWF ancla)."""

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    altitud_m: int | None = Field(description="Altitud media de la celda en el modelo.")


class DiaDistritoLluvia(Contrato):
    nivel: NivelLluvia | None = Field(description="None: ningún sistema ECMWF tuvo dato.")
    probabilidades: list[Porcentaje] | None = Field(
        min_length=3,
        max_length=3,
        description="P(≥T1), P(≥T2) y P(≥T3) de la zona del distrito, en %.",
    )

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if (self.nivel is None) != (self.probabilidades is None):
            raise ValueError("nivel y probabilidades van juntos")
        p = self.probabilidades
        if p is not None and not p[0] >= p[1] >= p[2]:
            raise ValueError("la probabilidad no puede crecer con el umbral")
        return self


class DistritoLluvia(Contrato):
    ubigeo: str = Field(pattern=r"^\d{6}$")
    zona: Zona
    celda: int | None = Field(ge=0, description="Índice en ``celdas``; None si no hubo dato.")
    mal_representado: bool = Field(
        description="La celda es mar o su altitud difiere demasiado de la capital."
    )
    dias: list[DiaDistritoLluvia] = Field(min_length=3, max_length=3)
    tendencia: Literal[1, 2, 3] | None


class LluviaDistritos(Contrato):
    """Semáforo de lluvia por distrito, sin verificar todavía."""

    version_esquema: Literal[1] = 1
    generado_en: FechaUtc
    verificacion: Literal["sin_verificar"]
    metodo: MetodoLluvia
    corridas: list[CorridaUsada] = Field(min_length=1)
    dias: list[DiaPronostico] = Field(min_length=3, max_length=3)
    tendencia: PeriodoTendencia
    celdas: list[CeldaModelo]
    distritos: list[DistritoLluvia] = Field(min_length=1)

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        sistemas = [c.sistema for c in self.corridas]
        if len(sistemas) != len(set(sistemas)):
            raise ValueError("un sistema aparece dos veces en corridas")
        if not {"ecmwf_ifs", "ecmwf_aifs"} & set(sistemas):
            raise ValueError("sin un sistema de ECMWF no se emite pronóstico")
        if any(b.inicio != a.fin for a, b in pairwise(self.dias)):
            raise ValueError("los días deben ser consecutivos")
        if (
            self.tendencia.inicio != self.dias[-1].fin
            or self.tendencia.fin <= self.tendencia.inicio
        ):
            raise ValueError("la tendencia empieza al terminar el último día")
        ubigeos = [d.ubigeo for d in self.distritos]
        if any(a >= b for a, b in pairwise(ubigeos)):
            raise ValueError("los distritos deben estar ordenados por ubigeo y sin repetir")
        if any(d.celda is not None and d.celda >= len(self.celdas) for d in self.distritos):
            raise ValueError("índice de celda fuera de rango")
        return self


# --- Archivo de pronósticos emitidos -----------------------------------------------------


class DiaArchivado(Contrato):
    """Un día de 12 a 12 UTC de una celda en un sistema."""

    inicio: FechaUtc
    validos: int = Field(ge=0, description="Miembros con dato ese día.")
    alcanzan: list[int] = Field(
        description="Miembros válidos con lluvia ≥ cada umbral de ``umbrales_conteo_mm``."
    )
    lluvia_mm: list[float | None] | None = Field(
        description="Lluvia por miembro (0 = control); None en sistemas no descargados ahora."
    )

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        if any(not 0 <= a <= self.validos for a in self.alcanzan):
            raise ValueError("un conteo no puede superar los miembros válidos")
        if self.lluvia_mm is not None and self.validos != sum(
            v is not None for v in self.lluvia_mm
        ):
            raise ValueError("validos no coincide con los valores presentes")
        return self


class CeldaArchivada(Contrato):
    id: str = Field(description="Nodo de 0.25° pedido, 'lat,lon' con dos decimales.")
    latitud: float = Field(ge=-90, le=90, description="Celda que devolvió el sistema.")
    longitud: float = Field(ge=-180, le=180)
    altitud_m: float | None
    dias: list[DiaArchivado] = Field(min_length=1)


class SistemaArchivado(Contrato):
    sistema: SistemaEnsamble
    modelo: str
    miembros: int = Field(ge=1)
    inicializacion: FechaUtc
    primer_dia: FechaUtc
    obtenido_en: FechaUtc
    celdas: list[CeldaArchivada] = Field(min_length=1)


class ArchivoLluvia(Contrato):
    """Un archivo por ejecución que descargó al menos un sistema (``.json.gz``)."""

    formato: Literal["radar-nino-norte/archivo-lluvia"]
    version_formato: Literal[1]
    generado_en: FechaUtc
    version_pipeline: str
    commit: str | None = Field(description="Commit del código que lo generó, si se conoce.")
    hora_corte_utc: Literal[12]
    umbrales_conteo_mm: list[float] = Field(min_length=1)
    descargados: list[SistemaEnsamble] = Field(
        description="Sistemas descargados en esta ejecución: solo ellos traen lluvia_mm."
    )
    sistemas: list[SistemaArchivado] = Field(
        description="Último dato de cada sistema conocido en ese momento."
    )
    pronostico: LluviaDistritos | None = Field(
        description="Producto emitido en esta ejecución; None si no se emitió."
    )

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        n = len(self.umbrales_conteo_mm)
        for sistema in self.sistemas:
            for celda in sistema.celdas:
                for dia in celda.dias:
                    if len(dia.alcanzan) != n:
                        raise ValueError("cada día debe tener un conteo por umbral")
                    tiene_valores = dia.lluvia_mm is not None
                    if tiene_valores != (sistema.sistema in self.descargados):
                        raise ValueError("solo los sistemas descargados traen valores")
                    if tiene_valores and len(dia.lluvia_mm or []) != sistema.miembros:
                        raise ValueError("número de miembros distinto del declarado")
        return self
