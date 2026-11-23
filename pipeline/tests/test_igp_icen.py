from datetime import UTC, datetime

import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.igp_icen import URL, FuenteIgpIcen, leer_tabla
from tests.ayudas import (
    AHORA,
    ICEN,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
    respuesta_fija,
    tiempo_agotado,
)

REAL = leer_fixture(ICEN)
CABECERA = "% Índice Costero El Niño (ICEN; ENFEN, 2024)\n% yy   mm   ICEN\n"


def _fuente(**opciones: object) -> FuenteIgpIcen:
    return FuenteIgpIcen(ahora=ahora_fijo, **opciones)  # type: ignore[arg-type]


def test_respuesta_real() -> None:
    bloque = _fuente().interpretar(REAL)

    assert bloque.url == URL
    assert bloque.obtenido_en == AHORA
    assert bloque.ultimo.model_dump() == {
        "anio": 2026,
        "mes": 9,
        "fecha": datetime(2026, 9, 1, tzinfo=UTC),
        "valor": 4.5,
    }
    assert bloque.fecha_dato == bloque.ultimo.fecha
    assert len(bloque.serie) == 36
    assert (bloque.serie[0].anio, bloque.serie[0].mes) == (2023, 10)


def test_serie_completa_desde_1950() -> None:
    serie = leer_tabla(REAL)

    assert (serie[0].anio, serie[0].mes, serie[0].valor) == (1950, 1, -0.75)
    assert len(serie) == 921


def test_obtener_usa_la_red_simulada() -> None:
    fuente = _fuente(cliente=cliente_simulado(respuesta_fija(REAL)), politica=politica_sin_espera())

    assert fuente.obtener().ultimo.valor == 4.5
    assert fuente.id == "igp-icen"


@pytest.mark.parametrize(
    "sucia",
    ["2026   9  -99.99", "2026   9    NaN", "2026   9", "2026  13   1.00", "2026   9   1.0  x"],
)
def test_filas_sucias_se_descartan_sin_rellenar(sucia: str) -> None:
    texto = CABECERA + "2026   7    3.38\n2026   8    3.98\n" + sucia + "\n"

    bloque = _fuente().interpretar(texto)

    assert bloque.ultimo.mes == 8
    assert [v.mes for v in bloque.serie] == [7, 8]


def test_hueco_en_la_serie_se_conserva() -> None:
    texto = CABECERA + "2026   6    2.66\n2026   7   -99.99\n2026   8    3.98\n"

    assert [v.mes for v in _fuente().interpretar(texto).serie] == [6, 8]


def test_serie_mas_corta_de_lo_esperado() -> None:
    texto = CABECERA + "2026   8    3.98\n2026   9    4.50\n"

    assert len(_fuente().interpretar(texto).serie) == 2


def test_cabecera_inesperada() -> None:
    texto = "% anio mes valor\n2026   9    4.50\n"

    with pytest.raises(FuenteNoDisponible, match="cabecera"):
        _fuente().interpretar(texto)


def test_sin_valores_validos() -> None:
    with pytest.raises(FuenteNoDisponible, match="sin ningún valor"):
        _fuente().interpretar(CABECERA + "2026   9  -99.99\n")


def test_meses_desordenados() -> None:
    with pytest.raises(FuenteNoDisponible, match="desordenados"):
        _fuente().interpretar(CABECERA + "2026   9    4.50\n2026   8    3.98\n")


def test_respuesta_html() -> None:
    html = respuesta_fija("<!DOCTYPE html><html><body>404</body></html>", tipo="text/html")
    fuente = _fuente(cliente=cliente_simulado(html), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()


def test_tiempo_de_espera_agotado() -> None:
    fuente = _fuente(cliente=cliente_simulado(tiempo_agotado), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="tiempo de espera"):
        fuente.obtener()


def test_meses_fuera_de_rango() -> None:
    with pytest.raises(ValueError, match="meses"):
        FuenteIgpIcen(meses=0)
