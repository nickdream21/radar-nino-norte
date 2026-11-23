from datetime import UTC, datetime, timedelta, timezone

import pytest

from radar.fuentes.dias_12utc import (
    CorteInexacto,
    acumular_dias_12utc,
    inicio_dia,
    primer_inicio_desde,
)

D = datetime(2026, 11, 23, tzinfo=UTC)
"""Medianoche UTC del día de referencia."""


def _serie(desde: datetime, hasta: datetime, paso_h: int) -> list[datetime]:
    paso = timedelta(hours=paso_h)
    fines = [desde]
    while fines[-1] + paso <= hasta:
        fines.append(fines[-1] + paso)
    return fines


def _marcas(fines: list[datetime], marcas: dict[datetime, float]) -> list[float | None]:
    """Cero en todas las horas salvo las marcadas, para ver a qué día va cada una."""
    return [marcas.get(f, 0.0) for f in fines]


@pytest.mark.parametrize(
    ("paso_h", "primera_del_dia"),
    [(1, 13), (3, 15), (6, 18)],
)
def test_bordes_del_dia(paso_h: int, primera_del_dia: int) -> None:
    # Serie de D 00:00 a D+2 00:00: el día D-1 (empezado antes) y el D+1 (sin terminar)
    # son parciales; solo el día D (D 12:00 → D+1 12:00) está completo.
    fines = _serie(D, D + timedelta(days=2), paso_h)
    hora_12 = D + timedelta(hours=12)
    marcas = {
        hora_12: 1000.0,  # termina a las 12 UTC del día D: pertenece al día D-1
        D + timedelta(hours=primera_del_dia): 1.0,  # primer intervalo del día D
        hora_12 + timedelta(days=1): 10.0,  # último intervalo del día D
        hora_12 + timedelta(days=1, hours=paso_h): 500.0,  # primero del día D+1
    }

    dias = acumular_dias_12utc(fines, _marcas(fines, marcas))

    assert dias == {hora_12: 11.0}


@pytest.mark.parametrize("paso_h", [1, 3, 6])
def test_suma_de_un_dia_completo(paso_h: int) -> None:
    inicio = D + timedelta(hours=12)
    fines = _serie(inicio, inicio + timedelta(days=1), paso_h)

    dias = acumular_dias_12utc(fines, [0.5] * len(fines))

    # El primer valor (que termina a las 12:00) no cuenta: es del día anterior.
    assert dias == {inicio: 0.5 * 24 // paso_h}


def test_pasos_mixtos_de_3_y_6_horas() -> None:
    # Como IFS: cada 3 h y, más allá de cierto plazo, cada 6 h.
    inicio = D + timedelta(hours=12)
    fines = _serie(inicio, inicio + timedelta(hours=12), 3) + _serie(
        inicio + timedelta(hours=18), inicio + timedelta(days=2), 6
    )

    dias = acumular_dias_12utc(fines, [1.0] * len(fines))

    assert dias == {inicio: 6.0, inicio + timedelta(days=1): 4.0}


def test_dia_parcial_al_principio_se_omite() -> None:
    # La serie empieza a las 13:00: el intervalo 12-13 del día D no se conoce.
    fines = _serie(D + timedelta(hours=13), D + timedelta(days=2, hours=12), 1)

    dias = acumular_dias_12utc(fines, [1.0] * len(fines))

    assert list(dias) == [D + timedelta(days=1, hours=12)]
    assert dias[D + timedelta(days=1, hours=12)] == 24.0


def test_dia_parcial_al_final_se_omite_sin_escalar() -> None:
    inicio = D + timedelta(hours=12)
    fines = _serie(inicio, inicio + timedelta(days=1, hours=21), 3)

    dias = acumular_dias_12utc(fines, [1.0] * len(fines))

    assert dias == {inicio: 8.0}


def test_serie_sin_dias_completos() -> None:
    fines = _serie(D, D + timedelta(hours=11), 1)

    assert acumular_dias_12utc(fines, [1.0] * len(fines)) == {}
    assert acumular_dias_12utc([D], [1.0]) == {}


@pytest.mark.parametrize("invalido", [None, float("nan"), float("inf"), -99.99, -1.0])
def test_valor_invalido_anula_solo_su_dia(invalido: float | None) -> None:
    inicio = D + timedelta(hours=12)
    fines = _serie(inicio, inicio + timedelta(days=2), 6)
    valores: list[float | None] = [2.0] * len(fines)
    valores[2] = invalido  # intervalo 18:00-00:00 del primer día

    dias = acumular_dias_12utc(fines, valores)

    assert dias == {inicio: None, inicio + timedelta(days=1): 8.0}


def test_negativos_pequenos_se_suman_y_el_total_no_baja_de_cero() -> None:
    # Ruido de desacumulación de Open-Meteo: -0.1 sueltos en días secos.
    inicio = D + timedelta(hours=12)
    fines = _serie(inicio, inicio + timedelta(days=2), 6)
    valores: list[float | None] = [0.0, -0.1, 0.0, 0.0, 0.0, 0.3, -0.1, 0.0, 0.0]

    dias = acumular_dias_12utc(fines, valores)

    assert dias == {inicio: 0.0, inicio + timedelta(days=1): 0.2}


def test_intervalo_que_cruza_las_12_utc() -> None:
    fines = [D + timedelta(hours=6), D + timedelta(hours=18)]

    with pytest.raises(CorteInexacto, match="cruza las 12 UTC"):
        acumular_dias_12utc(fines, [0.0, 1.0])


def test_pasos_de_4_horas_desalineados() -> None:
    fines = _serie(D + timedelta(hours=10), D + timedelta(days=1), 4)

    with pytest.raises(CorteInexacto):
        acumular_dias_12utc(fines, [1.0] * len(fines))


def test_horas_en_otra_zona_se_cortan_a_las_7_de_lima() -> None:
    lima = timezone(timedelta(hours=-5))
    inicio_lima = datetime(2026, 11, 23, 7, tzinfo=lima)
    fines = _serie(inicio_lima, inicio_lima + timedelta(days=1), 3)

    dias = acumular_dias_12utc(fines, [1.0] * len(fines))

    assert dias == {D + timedelta(hours=12): 8.0}
    assert next(iter(dias)).tzinfo == UTC


def test_errores_de_uso() -> None:
    with pytest.raises(ValueError, match="distinta longitud"):
        acumular_dias_12utc([D, D + timedelta(hours=1)], [1.0])
    with pytest.raises(ValueError, match="zona horaria"):
        acumular_dias_12utc([datetime(2026, 11, 23)], [1.0])  # noqa: DTZ001
    with pytest.raises(ValueError, match="no crecientes"):
        acumular_dias_12utc([D, D], [1.0, 1.0])


@pytest.mark.parametrize(
    ("instante", "dia", "primero"),
    [
        (D + timedelta(hours=12), D + timedelta(hours=12), D + timedelta(hours=12)),
        (D + timedelta(hours=11, minutes=59), D - timedelta(hours=12), D + timedelta(hours=12)),
        (D + timedelta(hours=18), D + timedelta(hours=12), D + timedelta(days=1, hours=12)),
        (D, D - timedelta(hours=12), D + timedelta(hours=12)),
    ],
)
def test_inicio_de_dia(instante: datetime, dia: datetime, primero: datetime) -> None:
    assert inicio_dia(instante) == dia
    assert primer_inicio_desde(instante) == primero
