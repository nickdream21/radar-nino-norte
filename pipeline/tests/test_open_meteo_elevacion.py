from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from radar.contratos.insumos_distritos import Punto
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.open_meteo_elevacion import (
    MAX_PUNTOS,
    FuenteOpenMeteoElevacion,
    url_consulta,
)
from tests.ayudas import (
    ELEVACION,
    ELEVACION_ERROR,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
)

PUNTOS: list[Punto] = [(-80.63, -5.19), (-78.51, -7.16), (-76.98282, -8.17)]


def test_respuesta_real() -> None:
    assert FuenteOpenMeteoElevacion.interpretar(leer_fixture(ELEVACION), 3) == [
        31.0,
        2703.0,
        1161.0,
    ]


def test_url_lleva_latitudes_y_longitudes_en_orden() -> None:
    consulta = parse_qs(urlparse(url_consulta(PUNTOS)).query)

    assert consulta["latitude"] == ["-5.19000,-7.16000,-8.17000"]
    assert consulta["longitude"] == ["-80.63000,-78.51000,-76.98282"]


@pytest.mark.parametrize("cantidad", [0, MAX_PUNTOS + 1])
def test_url_limita_los_puntos_por_llamada(cantidad: int) -> None:
    with pytest.raises(ValueError, match="por llamada"):
        url_consulta([(-80.0, -5.0)] * cantidad)


def test_agrupa_de_a_cien_puntos_por_llamada() -> None:
    llamadas: list[int] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        n = len(parse_qs(request.url.query.decode())["latitude"][0].split(","))
        llamadas.append(n)
        cuerpo = '{"elevation": [' + ", ".join(["100.0"] * n) + "]}"
        return httpx.Response(200, text=cuerpo, headers={"content-type": "application/json"})

    fuente = FuenteOpenMeteoElevacion(
        [(-80.0, -5.0)] * 250,
        cliente=cliente_simulado(manejador),
        politica=politica_sin_espera(),
    )

    assert len(fuente.obtener().metros) == 250
    assert llamadas == [100, 100, 50]
    assert fuente.id == "open-meteo-elevacion"


def test_sin_puntos_no_se_construye() -> None:
    with pytest.raises(ValueError, match="no hay puntos"):
        FuenteOpenMeteoElevacion([])


@pytest.mark.parametrize(
    ("texto", "motivo"),
    [
        ('{"elevation": [10.0, NaN, 3.0]}', "sin altitud válida"),
        ('{"elevation": [10.0, -9999.0, 3.0]}', "sin altitud válida"),
        ('{"elevation": [10.0, null, 3.0]}', "no numérica"),
        ('{"elevation": [10.0, true, 3.0]}', "no numérica"),
        ('{"elevation": [10.0, 3.0]}', "llegaron 2"),
        ('{"elevacion": []}', "lista de altitudes"),
        ("[1, 2, 3]", "lista de altitudes"),
        ("no es json", "no es JSON"),
    ],
)
def test_respuestas_sucias(texto: str, motivo: str) -> None:
    with pytest.raises(FuenteNoDisponible, match=motivo):
        FuenteOpenMeteoElevacion.interpretar(texto, 3)


def test_error_de_la_api() -> None:
    with pytest.raises(FuenteNoDisponible, match="Latitude must be in range"):
        FuenteOpenMeteoElevacion.interpretar(leer_fixture(ELEVACION_ERROR), 1)


def test_cuota_agotada_se_reintenta_y_falla() -> None:
    def cuota(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, text='{"error": true, "reason": "Daily API request limit exceeded"}'
        )

    fuente = FuenteOpenMeteoElevacion(
        PUNTOS, cliente=cliente_simulado(cuota), politica=politica_sin_espera(intentos=2)
    )
    with pytest.raises(FuenteNoDisponible, match="HTTP 429 tras 2 intentos"):
        fuente.obtener()
