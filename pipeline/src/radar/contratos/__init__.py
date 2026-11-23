"""Contratos de datos entre el pipeline y la web.

Única fuente de verdad: los esquemas JSON y los tipos TypeScript se generan desde aquí.
Todo contrato nuevo debe registrarse en ``CONTRATOS`` para que se exporte.
"""

from pydantic import BaseModel

from radar.contratos.manifiesto import Manifiesto, ProductoPublicado

CONTRATOS: dict[str, type[BaseModel]] = {
    "manifiesto": Manifiesto,
}

__all__ = ["CONTRATOS", "Manifiesto", "ProductoPublicado"]
