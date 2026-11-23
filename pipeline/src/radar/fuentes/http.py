"""Descarga HTTP común a los adaptadores: tiempo de espera y reintentos acotados.

Toda llamada de red de las fuentes pasa por aquí. Un fallo se traduce siempre en
``FuenteNoDisponible``; nunca se devuelve un cuerpo a medias ni una página de error.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from radar.fuentes.base import FuenteNoDisponible

registro = logging.getLogger(__name__)

TIEMPO_ESPERA = httpx.Timeout(30.0, connect=10.0)
"""30 s por lectura y 10 s para conectar: los archivos pesan como mucho unos cientos de kB."""

ESTADOS_REINTENTABLES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class PoliticaReintentos:
    """Número máximo de intentos y espera creciente entre ellos."""

    intentos: int = 3
    espera_inicial_s: float = 2.0
    factor: float = 2.0
    esperar: Callable[[float], None] = field(default=time.sleep, repr=False)

    def __post_init__(self) -> None:
        if self.intentos < 1:
            raise ValueError("debe haber al menos un intento")


def _parece_html(respuesta: httpx.Response) -> bool:
    tipo = respuesta.headers.get("content-type", "").lower()
    if "html" in tipo:
        return True
    inicio = respuesta.content[:512].lstrip().lower()
    return inicio.startswith((b"<!doctype", b"<html", b"<?xml", b"<head", b"<body"))


def descargar_texto(
    fuente: str,
    url: str,
    *,
    formulario: dict[str, str] | None = None,
    cabeceras: dict[str, str] | None = None,
    cliente: httpx.Client | None = None,
    politica: PoliticaReintentos | None = None,
) -> str:
    """Descarga ``url`` como texto o lanza ``FuenteNoDisponible``.

    Reintenta ante tiempos de espera, errores de conexión y respuestas 429/5xx.
    Un 4xx distinto de 429 no se reintenta: no se arreglará solo. Una respuesta
    HTML (portal caído, página de captcha) se rechaza aunque llegue con 200.
    Con ``formulario`` la petición es un POST con esos campos (consultas largas).
    """
    return _descargar(
        fuente, url, formulario=formulario, cabeceras=cabeceras, cliente=cliente, politica=politica
    ).text


def descargar_bytes(
    fuente: str,
    url: str,
    *,
    cliente: httpx.Client | None = None,
    politica: PoliticaReintentos | None = None,
) -> bytes:
    """Como ``descargar_texto``, pero devuelve el cuerpo sin decodificar (p. ej. un ZIP)."""
    return _descargar(fuente, url, cliente=cliente, politica=politica).content


def _descargar(
    fuente: str,
    url: str,
    *,
    formulario: dict[str, str] | None = None,
    cabeceras: dict[str, str] | None = None,
    cliente: httpx.Client | None = None,
    politica: PoliticaReintentos | None = None,
) -> httpx.Response:
    politica = politica or PoliticaReintentos()
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=TIEMPO_ESPERA, follow_redirects=True)
    ultimo_motivo = "sin intentos"
    try:
        for intento in range(1, politica.intentos + 1):
            try:
                if formulario is None:
                    respuesta = cliente.get(url, headers=cabeceras)
                else:
                    respuesta = cliente.post(url, data=formulario, headers=cabeceras)
            except httpx.TimeoutException:
                ultimo_motivo = "tiempo de espera agotado"
            except httpx.RequestError as error:
                ultimo_motivo = f"error de conexión ({type(error).__name__})"
            else:
                if respuesta.status_code == 200:
                    if _parece_html(respuesta):
                        raise FuenteNoDisponible(fuente, "respondió HTML o XML en lugar de datos")
                    return respuesta
                ultimo_motivo = f"HTTP {respuesta.status_code}"
                if respuesta.status_code not in ESTADOS_REINTENTABLES:
                    raise FuenteNoDisponible(fuente, ultimo_motivo)
            if intento < politica.intentos:
                espera = politica.espera_inicial_s * politica.factor ** (intento - 1)
                registro.warning(
                    "%s: intento %d de %d fallido (%s); reintento en %.0f s",
                    fuente,
                    intento,
                    politica.intentos,
                    ultimo_motivo,
                    espera,
                )
                politica.esperar(espera)
    finally:
        if propio:
            cliente.close()
    raise FuenteNoDisponible(fuente, f"{ultimo_motivo} tras {politica.intentos} intentos")
