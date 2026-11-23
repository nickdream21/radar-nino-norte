"""ENFEN: estado del sistema de alerta, mantenido a mano.

El ENFEN solo publica comunicados en PDF, así que una persona copia el estado, el
número, la fecha y el enlace del último comunicado en ``datos-estaticos/enfen.json``.
Este adaptador lo lee y valida; no consulta la red.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from radar.contratos import BloqueEnfen, ComunicadoEnfen
from radar.fuentes.base import FuenteNoDisponible

FUENTE = "ENFEN (comunicado oficial, transcrito a mano)"


class FuenteEnfenEstatica:
    """Lee el último comunicado ENFEN de un archivo JSON del repositorio."""

    def __init__(
        self, ruta: Path, *, ahora: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._ruta = ruta
        self._ahora = ahora

    @property
    def id(self) -> str:
        return "enfen-estatico"

    def obtener(self) -> BloqueEnfen:
        try:
            texto = self._ruta.read_text(encoding="utf-8")
        except OSError as error:
            raise FuenteNoDisponible(FUENTE, f"no se pudo leer {self._ruta.name}") from error
        try:
            comunicado = ComunicadoEnfen.model_validate_json(texto)
        except ValidationError as error:
            raise FuenteNoDisponible(FUENTE, f"{self._ruta.name} no es válido: {error}") from error
        return BloqueEnfen(
            fuente=FUENTE,
            url=comunicado.enlace,
            fecha_dato=comunicado.fecha,
            obtenido_en=self._ahora(),
            comunicado=comunicado,
        )
