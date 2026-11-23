"""Utilidades compartidas por las pruebas."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from radar.fuentes.http import PoliticaReintentos

FIXTURES = Path(__file__).parent / "fixtures"
AHORA = datetime(2026, 11, 23, 15, 0, tzinfo=UTC)

CPC = "noaa_cpc_wksst9120_2026-11-23.for"
ICEN = "igp_icen_2026-11-23.txt"
CRW = "crw_dhw_5km_paita_2026-11-23.json"
CRW_ERROR = "crw_error_erddap.txt"


def leer_fixture(nombre: str) -> str:
    """Respuesta grabada de una fuente real."""
    return (FIXTURES / nombre).read_text(encoding="utf-8")


def ahora_fijo() -> datetime:
    return AHORA


class Esperas(list[float]):
    """Registra las esperas entre reintentos en lugar de dormir."""

    def __call__(self, segundos: float) -> None:
        self.append(segundos)


def politica_sin_espera(esperas: Esperas | None = None, intentos: int = 3) -> PoliticaReintentos:
    return PoliticaReintentos(
        intentos=intentos, esperar=esperas if esperas is not None else Esperas()
    )


def cliente_simulado(manejador: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    """Cliente HTTP que responde con ``manejador`` sin tocar la red."""
    return httpx.Client(transport=httpx.MockTransport(manejador))


def respuesta_fija(
    texto: str, estado: int = 200, tipo: str = "text/plain"
) -> Callable[[httpx.Request], httpx.Response]:
    def manejador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(estado, text=texto, headers={"content-type": tipo})

    return manejador


def tiempo_agotado(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("sin respuesta", request=request)
