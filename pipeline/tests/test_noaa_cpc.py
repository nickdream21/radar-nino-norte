from datetime import UTC, datetime

import pytest

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.noaa_cpc import URL, FuenteNoaaCpcSemanal, leer_tabla
from tests.ayudas import (
    AHORA,
    CPC,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
    respuesta_fija,
    tiempo_agotado,
)

REAL = leer_fixture(CPC)
CABECERA = "\n".join(REAL.splitlines()[:4])


def _tabla(*filas: str) -> str:
    return CABECERA + "\n" + "\n".join(filas) + "\n"


def _fuente(**opciones: object) -> FuenteNoaaCpcSemanal:
    return FuenteNoaaCpcSemanal(ahora=ahora_fijo, **opciones)  # type: ignore[arg-type]


def test_respuesta_real() -> None:
    bloque = _fuente().interpretar(REAL)

    assert bloque.url == URL
    assert bloque.obtenido_en == AHORA
    assert bloque.fecha_dato == datetime(2026, 11, 11, tzinfo=UTC)
    assert bloque.nino12.ultimo.model_dump() == {
        "fecha": datetime(2026, 11, 11, tzinfo=UTC),
        "temperatura": 27.1,
        "anomalia": 5.4,
    }
    assert (bloque.nino34.ultimo.temperatura, bloque.nino34.ultimo.anomalia) == (29.9, 3.2)
    assert len(bloque.nino12.serie) == len(bloque.nino34.serie) == 104
    assert bloque.nino12.serie[0].fecha == datetime(2024, 11, 20, tzinfo=UTC)


def test_lee_anomalias_negativas_pegadas_a_la_temperatura() -> None:
    series = leer_tabla(REAL)

    primero = series["Nino1+2"][0]
    assert (primero.fecha, primero.temperatura, primero.anomalia) == (
        datetime(1981, 9, 2, tzinfo=UTC),
        20.6,
        -0.1,
    )
    assert series["Nino4"][0].anomalia == -0.3


def test_obtener_usa_la_red_simulada() -> None:
    fuente = _fuente(cliente=cliente_simulado(respuesta_fija(REAL)), politica=politica_sin_espera())

    assert fuente.obtener().nino12.ultimo.anomalia == 5.4
    assert fuente.id == "noaa-cpc-semanal"


@pytest.mark.parametrize("centinela", ["-99.9", " NaN", "-999"])
def test_centinela_se_descarta_solo_en_su_region(centinela: str) -> None:
    texto = _tabla(
        " 04NOV2026     27.0 5.6     29.5 4.4     30.1 3.3     30.1 1.5",
        f" 11NOV2026     27.1{centinela:>4}     29.4 4.3     29.9 3.2     29.9 1.3",
    )

    bloque = _fuente().interpretar(texto)

    assert bloque.nino12.ultimo.fecha == datetime(2026, 11, 4, tzinfo=UTC)
    assert bloque.nino34.ultimo.fecha == datetime(2026, 11, 11, tzinfo=UTC)
    assert len(bloque.nino12.serie) == 1  # hueco, no relleno
    assert bloque.fecha_dato == datetime(2026, 11, 11, tzinfo=UTC)


def test_linea_incompleta_y_fecha_invalida_se_descartan() -> None:
    texto = _tabla(
        " 04NOV2026     27.0 5.6     29.5 4.4     30.1 3.3     30.1 1.5",
        " 11NOV2026     27.1 5.4     29.4",
        " 11XXX2026     27.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3",
    )

    bloque = _fuente().interpretar(texto)

    assert bloque.nino12.serie == [bloque.nino12.ultimo]
    assert bloque.nino12.ultimo.fecha == datetime(2026, 11, 4, tzinfo=UTC)


def test_serie_mas_corta_de_lo_esperado_no_se_rellena() -> None:
    filas = REAL.splitlines()[4:7]

    bloque = _fuente().interpretar(_tabla(*filas))

    assert len(bloque.nino12.serie) == 3
    assert len(bloque.nino34.serie) == 3


@pytest.mark.parametrize(
    "cabecera",
    [
        "                Nino1+2      Nino3        Nino4        Nino34\n Week          SST SSTA",
        "                Nino1+2      Nino3        Nino34        Nino4\n Week          SST ANOM",
        "Weekly SST data\n\n",
    ],
)
def test_cabecera_inesperada(cabecera: str) -> None:
    texto = cabecera + "\n 11NOV2026     27.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3\n"

    with pytest.raises(FuenteNoDisponible, match="cabecera"):
        _fuente().interpretar(texto)


def test_fechas_repetidas_fallan() -> None:
    fila = " 11NOV2026     27.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3"

    with pytest.raises(FuenteNoDisponible, match="desordenadas"):
        _fuente().interpretar(_tabla(fila, fila))


def test_region_sin_ningun_valor_falla() -> None:
    texto = _tabla(" 11NOV2026    -99.9-99.9     29.4 4.3     29.9 3.2     29.9 1.3")

    with pytest.raises(FuenteNoDisponible, match="Niño 1\\+2 sin ningún valor"):
        _fuente().interpretar(texto)


def test_valor_fuera_de_rango_se_descarta() -> None:
    texto = _tabla(
        " 04NOV2026     27.0 5.6     29.5 4.4     30.1 3.3     30.1 1.5",
        " 11NOV2026     87.1 5.4     29.4 4.3     29.9 3.2     29.9 1.3",
    )

    assert _fuente().interpretar(texto).nino12.ultimo.temperatura == 27.0


def test_respuesta_html() -> None:
    html = respuesta_fija("<html><body>Service Unavailable</body></html>", tipo="text/html")
    fuente = _fuente(cliente=cliente_simulado(html), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="HTML"):
        fuente.obtener()


def test_tiempo_de_espera_agotado() -> None:
    fuente = _fuente(cliente=cliente_simulado(tiempo_agotado), politica=politica_sin_espera())

    with pytest.raises(FuenteNoDisponible, match="tiempo de espera"):
        fuente.obtener()


def test_semanas_fuera_de_rango() -> None:
    with pytest.raises(ValueError, match="semanas"):
        FuenteNoaaCpcSemanal(semanas=105)
