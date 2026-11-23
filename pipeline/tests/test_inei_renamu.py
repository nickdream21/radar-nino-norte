import io
import zipfile

import httpx
import pytest

from radar.contratos import DEPARTAMENTOS
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.inei_renamu import URL, FuenteIneiRenamu
from tests.ayudas import (
    RENAMU,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
    respuesta_fija,
)

REAL = leer_fixture(RENAMU)
CABECERA = "Año;idmunici;ccdd;ccpp;ccdi;Ubigeo;Departamento;Provincia;Distrito;Tipomuni"


def _zip(texto: str, nombre: str = "Base.csv", codificacion: str = "utf-8") -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as archivo:
        archivo.writestr(nombre, texto.encode(codificacion))
    return memoria.getvalue()


def _fuente(departamentos: tuple[str, ...] = ("24",), **opciones: object) -> FuenteIneiRenamu:
    return FuenteIneiRenamu(departamentos, **opciones)  # type: ignore[arg-type]


def _csv(*filas: str) -> str:
    return "\n".join([CABECERA, *filas]) + "\n"


def test_respuesta_real_cuenta_los_distritos_de_los_cinco_departamentos() -> None:
    lista = _fuente(tuple(DEPARTAMENTOS)).interpretar_csv(REAL)

    por_departamento: dict[str, int] = {}
    for distrito in lista.distritos:
        por_departamento[distrito.ubigeo[:2]] = por_departamento.get(distrito.ubigeo[:2], 0) + 1
    assert por_departamento == {"06": 127, "13": 84, "14": 38, "20": 65, "24": 13}
    assert lista.anio == 2026
    nuevo = next(d for d in lista.distritos if d.ubigeo == "130112")
    assert (nuevo.nombre, nuevo.provincia) == ("ALTO TRUJILLO", "TRUJILLO")
    assert [d.ubigeo for d in lista.distritos] == sorted(d.ubigeo for d in lista.distritos)


def test_obtener_descarga_el_zip() -> None:
    pedidas: list[str] = []

    def manejador(request: httpx.Request) -> httpx.Response:
        pedidas.append(str(request.url))
        return httpx.Response(200, content=_zip(REAL), headers={"content-type": "application/zip"})

    fuente = _fuente(cliente=cliente_simulado(manejador), politica=politica_sin_espera())

    assert len(fuente.obtener().distritos) == 13
    assert pedidas == [URL]
    assert fuente.id == "inei-renamu"


def test_zip_en_windows_1252() -> None:
    texto = _csv(
        "2026;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1",
        "2026;240102;24;01;02;240102;TUMBES;TUMBES;CORRALES;2",
    )
    contenido = _zip(texto, codificacion="cp1252")

    def manejador(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=contenido)

    lista = _fuente(cliente=cliente_simulado(manejador), politica=politica_sin_espera()).obtener()

    assert [d.nombre for d in lista.distritos] == ["TUMBES", "CORRALES"]


def test_ubigeo_sin_cero_inicial_se_repara() -> None:
    lista = _fuente(("06",)).interpretar_csv(
        _csv("2026;060101;06;01;01;60101;CAJAMARCA;CAJAMARCA;CAJAMARCA;1")
    )

    assert lista.distritos[0].ubigeo == "060101"


def test_fila_incompleta_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="fila 3 incompleta"):
        _fuente().interpretar_csv(
            _csv("2026;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1", "2026;240102;24")
        )


def test_nombre_vacio_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="fila 2 no válida"):
        _fuente().interpretar_csv(_csv("2026;240101;24;01;01;240101;TUMBES;TUMBES;;1"))


def test_lineas_vacias_y_otros_departamentos_se_ignoran() -> None:
    lista = _fuente().interpretar_csv(
        _csv(
            ";;;;;;;;;",
            "2026;010101;01;01;01;010101;AMAZONAS;CHACHAPOYAS;CHACHAPOYAS;1",
            "2026;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1",
        )
    )

    assert [d.ubigeo for d in lista.distritos] == ["240101"]


def test_ubigeo_repetido_falla() -> None:
    fila = "2026;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1"
    with pytest.raises(FuenteNoDisponible, match="lista no válida"):
        _fuente().interpretar_csv(_csv(fila, fila))


def test_otro_anio_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match="año 2026"):
        _fuente().interpretar_csv(_csv("2025;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1"))


def test_departamento_sin_distritos_falla() -> None:
    with pytest.raises(FuenteNoDisponible, match=r"sin distritos .*'20'"):
        _fuente(("24", "20")).interpretar_csv(
            _csv("2026;240101;24;01;01;240101;TUMBES;TUMBES;TUMBES;1")
        )


@pytest.mark.parametrize("texto", ["", "a;b;c\n1;2;3\n"])
def test_sin_las_columnas_esperadas(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible, match="columnas esperadas"):
        _fuente().interpretar_csv(texto)


def test_zip_sin_csv_o_dañado() -> None:
    for contenido in (_zip("hola", nombre="leeme.txt"), b"PK\x03\x04 roto"):

        def manejador(_: httpx.Request, cuerpo: bytes = contenido) -> httpx.Response:
            return httpx.Response(200, content=cuerpo)

        fuente = _fuente(cliente=cliente_simulado(manejador), politica=politica_sin_espera())
        with pytest.raises(FuenteNoDisponible, match="ZIP"):
            fuente.obtener()


def test_portal_responde_html() -> None:
    html = respuesta_fija("<html><body>Mantenimiento</body></html>", tipo="text/html")
    fuente = _fuente(cliente=cliente_simulado(html), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()
