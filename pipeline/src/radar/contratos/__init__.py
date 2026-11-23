"""Contratos de datos entre el pipeline y la web.

Única fuente de verdad: los esquemas JSON y los tipos TypeScript se generan desde aquí.
Todo contrato nuevo debe registrarse en ``CONTRATOS`` para que se exporte.
"""

from pydantic import BaseModel

from radar.contratos.base import Contrato, FechaUtc
from radar.contratos.distritos import (
    DEPARTAMENTOS,
    CapitalDistrital,
    CatalogoDistritos,
    Distrito,
    FuenteCatalogo,
    Vertiente,
    Zona,
)
from radar.contratos.lluvia import (
    ArchivoLluvia,
    LluviaDistritos,
    SistemaArchivado,
)
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
    "catalogo_distritos": CatalogoDistritos,
    "lluvia_distritos": LluviaDistritos,
}

__all__ = [
    "CONTRATOS",
    "DEPARTAMENTOS",
    "ArchivoLluvia",
    "Bloque",
    "BloqueEnfen",
    "BloqueIcen",
    "BloqueIndicesSemanales",
    "BloqueMarPaita",
    "Caja",
    "CapitalDistrital",
    "CatalogoDistritos",
    "ComunicadoEnfen",
    "Contrato",
    "Distrito",
    "EstadoNino",
    "FechaUtc",
    "FuenteCatalogo",
    "IndiceSemanal",
    "LluviaDistritos",
    "Manifiesto",
    "ProductoPublicado",
    "SistemaArchivado",
    "ValorMensual",
    "ValorSemanal",
    "Vertiente",
    "Zona",
]
