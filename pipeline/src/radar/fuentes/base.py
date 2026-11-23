"""Interfaz común de las fuentes de datos externas.

El resto del pipeline depende solo de esta interfaz, nunca de un proveedor concreto,
para poder reemplazar una fuente sin tocar modelos ni publicación (ADR 0003).
"""

from typing import Protocol


class FuenteNoDisponible(Exception):
    """La fuente no respondió o devolvió datos inválidos.

    Quien la captura debe conservar el último dato válido, no fabricar uno.
    """

    def __init__(self, fuente: str, motivo: str) -> None:
        super().__init__(f"{fuente}: {motivo}")
        self.fuente = fuente
        self.motivo = motivo


class FuenteDatos[T](Protocol):
    """Una fuente que entrega un valor ya validado de tipo ``T``."""

    @property
    def id(self) -> str:
        """Identificador estable de la fuente, usado en registros y atribución."""
        ...

    def obtener(self) -> T:
        """Devuelve el dato más reciente o lanza ``FuenteNoDisponible``."""
        ...
