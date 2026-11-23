"""Contratos de datos entre el pipeline y la web.

Única fuente de verdad: los esquemas JSON y los tipos TypeScript se generan desde aquí.
Todo contrato nuevo debe registrarse en ``CONTRATOS`` para que se exporte.
"""

from pydantic import BaseModel

from radar.contratos.base import Contrato, FechaUtc
from radar.contratos.manifiesto import Manifiesto, ProductoPublicado
from radar.contratos.nino import (
    Bloque,
    BloqueEnfen,
    BloqueIcen,
    BloqueIndicesSemanales,
    BloqueMarPaita,
    Caja,
    ComunicadoEnfen,
    EstadoNino,
    IndiceSemanal,
    ValorMensual,
    ValorSemanal,
)

CONTRATOS: dict[str, type[BaseModel]] = {
    "manifiesto": Manifiesto,
    "estado_nino": EstadoNino,
}

__all__ = [
    "CONTRATOS",
    "Bloque",
    "BloqueEnfen",
    "BloqueIcen",
    "BloqueIndicesSemanales",
    "BloqueMarPaita",
    "Caja",
    "ComunicadoEnfen",
    "Contrato",
    "EstadoNino",
    "FechaUtc",
    "IndiceSemanal",
    "Manifiesto",
    "ProductoPublicado",
    "ValorMensual",
    "ValorSemanal",
]
