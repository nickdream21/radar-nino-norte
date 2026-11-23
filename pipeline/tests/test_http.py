import httpx
import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.http import PoliticaReintentos, descargar_bytes, descargar_texto
from tests.ayudas import Esperas, cliente_simulado, politica_sin_espera, respuesta_fija

URL = "https://ejemplo.test/datos.txt"


def test_devuelve_el_texto() -> None:
    cliente = cliente_simulado(respuesta_fija("hola"))

    assert descargar_texto("prueba", URL, cliente=cliente, politica=politica_sin_espera()) == "hola"


def test_reintenta_ante_5xx_y_luego_responde() -> None:
    respuestas = iter([httpx.Response(503), httpx.Response(200, text="ok")])
    esperas = Esperas()

    texto = descargar_texto(
        "prueba",
        URL,
        cliente=cliente_simulado(lambda _: next(respuestas)),
        politica=politica_sin_espera(esperas),
    )

    assert texto == "ok"
    assert esperas == [2.0]


def test_tiempo_de_espera_agotado_tras_intentos_acotados() -> None:
    llamadas = 0

    def lento(request: httpx.Request) -> httpx.Response:
        nonlocal llamadas
        llamadas += 1
        raise httpx.ReadTimeout("lento", request=request)

    esperas = Esperas()
    with pytest.raises(FuenteNoDisponible, match="tiempo de espera agotado tras 3 intentos"):
        descargar_texto(
            "prueba", URL, cliente=cliente_simulado(lento), politica=politica_sin_espera(esperas)
        )

    assert llamadas == 3
    assert esperas == [2.0, 4.0]


def test_404_no_se_reintenta() -> None:
    llamadas = 0

    def no_existe(_: httpx.Request) -> httpx.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx.Response(404)

    with pytest.raises(FuenteNoDisponible, match="HTTP 404"):
        descargar_texto(
            "prueba", URL, cliente=cliente_simulado(no_existe), politica=politica_sin_espera()
        )
    assert llamadas == 1


@pytest.mark.parametrize(
    ("cuerpo", "tipo"),
    [
        ("<html><body>Mantenimiento</body></html>", "text/html"),
        ("<!DOCTYPE html><title>Just a moment...</title>", "text/plain"),
        ('<?xml version="1.0" ?><ServiceExceptionReport/>', "text/xml;charset=UTF-8"),
    ],
)
def test_html_en_lugar_de_datos(cuerpo: str, tipo: str) -> None:
    with pytest.raises(FuenteNoDisponible, match="HTML"):
        descargar_texto(
            "prueba",
            URL,
            cliente=cliente_simulado(respuesta_fija(cuerpo, tipo=tipo)),
            politica=politica_sin_espera(),
        )


def test_sin_cliente_usa_uno_propio_con_tiempo_de_espera() -> None:
    # La red está bloqueada en las pruebas: el cliente propio falla como sin conexión.
    with pytest.raises(FuenteNoDisponible, match="error de conexión"):
        descargar_texto("prueba", URL, politica=politica_sin_espera(intentos=1))


def test_politica_exige_un_intento() -> None:
    with pytest.raises(ValueError, match="al menos un intento"):
        PoliticaReintentos(intentos=0)


def test_descarga_binaria_sin_decodificar() -> None:
    contenido = b"PK\x03\x04\xff\xfe"

    def zip_(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=contenido, headers={"content-type": "application/zip"})

    assert (
        descargar_bytes(
            "prueba", URL, cliente=cliente_simulado(zip_), politica=politica_sin_espera()
        )
        == contenido
    )


def test_formulario_se_envia_por_post_con_cabeceras() -> None:
    recibidas: list[httpx.Request] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        recibidas.append(request)
        return httpx.Response(200, text="{}")

    descargar_texto(
        "prueba",
        URL,
        formulario={"query": "SELECT 1"},
        cabeceras={"User-Agent": "prueba/1.0"},
        cliente=cliente_simulado(manejador),
        politica=politica_sin_espera(),
    )

    assert recibidas[0].method == "POST"
    assert recibidas[0].content == b"query=SELECT+1"
    assert recibidas[0].headers["User-Agent"] == "prueba/1.0"
