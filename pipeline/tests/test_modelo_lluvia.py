from datetime import UTC, datetime, timedelta
from fractions import Fraction

import pytest

from radar.fuentes.open_meteo_ensambles import Sistema
from radar.modelos import lluvia as m1

IFS, AIFS, GEFS = Sistema.IFS, Sistema.AIFS, Sistema.GEFS
T0 = datetime(2026, 11, 23, 0, tzinfo=UTC)


# --- Niveles: bordes exactos de 30 %, 10 % y 70 % ---------------------------------------


@pytest.mark.parametrize(
    ("p", "esperado"),
    [
        ((0, 0, 0), m1.VERDE),
        ((29, 0, 0), m1.VERDE),
        ((30, 0, 0), m1.AMARILLO),
        ((100, 29, 9), m1.AMARILLO),
        ((100, 30, 0), m1.NARANJA),
        ((100, 10, 10), m1.NARANJA),
        ((100, 69, 29), m1.NARANJA),
        ((100, 30, 30), m1.ROJO),
        ((100, 70, 0), m1.ROJO),
    ],
)
def test_nivel_en_los_bordes(p: tuple[int, int, int], esperado: m1.Nivel) -> None:
    assert m1.nivel(*p) == esperado


def test_probabilidad_exactamente_en_el_umbral_activa_el_nivel() -> None:
    # 3 de 10 miembros: exactamente el 30 %, sin errores de coma flotante.
    conteo = m1.contar([5.0] * 3 + [0.0] * 7, umbrales=(5.0,))
    p = m1.probabilidad(conteo, 5.0, umbrales=(5.0,))
    assert p == Fraction(3, 10)
    assert m1.porcentaje(m1.mezclar({IFS: p})) == 30  # type: ignore[arg-type]


# --- Conteos y probabilidad por sistema --------------------------------------------------


def test_lluvia_igual_al_umbral_cuenta_y_los_nulos_no() -> None:
    conteo = m1.contar([10.0, 9.99, None, 40.0, None], umbrales=(10.0, 40.0))

    assert conteo == m1.Conteo(validos=3, alcanzan=(2, 1))
    assert m1.probabilidad(conteo, 10.0, umbrales=(10.0, 40.0)) == Fraction(2, 3)


def test_dia_sin_miembros_validos_no_tiene_probabilidad() -> None:
    conteo = m1.contar([None, None])

    assert conteo.validos == 0
    assert m1.probabilidad(conteo, 10.0) is None
    dia = m1.dia_distrito({IFS: conteo, AIFS: None, GEFS: None}, m1.UMBRALES_MM["A"])
    assert dia == m1.DiaDistrito(nivel=None, porcentajes=None)


def test_umbrales_de_conteo_cubren_todas_las_zonas() -> None:
    todos = {t for ts in m1.UMBRALES_MM.values() for t in ts}
    assert set(m1.UMBRALES_CONTEO_MM) == todos
    assert list(m1.UMBRALES_CONTEO_MM) == sorted(todos)


# --- Mezcla -----------------------------------------------------------------------------


def test_mezcla_con_los_tres_sistemas() -> None:
    p = m1.mezclar({IFS: Fraction(1), AIFS: Fraction(0), GEFS: Fraction(1, 2)})
    assert p == Fraction(1, 2) + Fraction(1, 8)


def test_sistema_ausente_renormaliza_los_pesos() -> None:
    p = m1.mezclar({IFS: Fraction(1), AIFS: None, GEFS: Fraction(0)})
    assert p == Fraction(2, 3)
    assert m1.pesos_normalizados([AIFS, GEFS]) == {AIFS: Fraction(1, 2), GEFS: Fraction(1, 2)}


def test_solo_gefs_no_se_emite() -> None:
    assert m1.mezclar({IFS: None, AIFS: None, GEFS: Fraction(1)}) is None
    assert m1.mezclar({GEFS: Fraction(1)}) is None
    solo_gefs = m1.dia_distrito({GEFS: m1.contar([50.0] * 31), IFS: None}, m1.UMBRALES_MM["B"])
    assert solo_gefs.nivel is None
    assert m1.elegir_corridas({GEFS: T0}) is None


@pytest.mark.parametrize(
    ("fraccion", "esperado"),
    [
        (Fraction(0), 0),
        (Fraction(1), 100),
        (Fraction(59, 200), 30),  # 29.5 % sube: mitad hacia arriba, no bancario
        (Fraction(589, 2000), 29),  # 29.45 %
        (Fraction(1, 200), 1),
        (Fraction(5, 200), 3),  # 2.5 %: ``round`` daría 2
    ],
)
def test_porcentaje_redondea_la_mitad_hacia_arriba(fraccion: Fraction, esperado: int) -> None:
    assert m1.porcentaje(fraccion) == esperado


def test_dia_distrito_completo() -> None:
    # IFS: todos 20 mm; AIFS y GEFS secos. Zona A (5/15/40): 50 %, 50 %, 0 %.
    dia = m1.dia_distrito(
        {IFS: m1.contar([20.0] * 51), AIFS: m1.contar([0.0] * 51), GEFS: m1.contar([0.0] * 31)},
        m1.UMBRALES_MM["A"],
    )
    assert dia == m1.DiaDistrito(nivel=m1.NARANJA, porcentajes=(50, 50, 0))


# --- Tendencia ---------------------------------------------------------------------------


def test_tendencia_tiene_tope_naranja() -> None:
    assert m1.tendencia([m1.VERDE, m1.ROJO, None, m1.AMARILLO]) == m1.NARANJA
    assert m1.tendencia([m1.VERDE, m1.AMARILLO]) == m1.AMARILLO
    assert m1.tendencia([None, None, None, None]) is None


# --- Corridas ----------------------------------------------------------------------------


def test_elegir_corridas_con_desfase() -> None:
    disponibles = {
        IFS: T0 + timedelta(hours=12),
        AIFS: T0,
        GEFS: T0 - timedelta(hours=1),
    }
    assert m1.elegir_corridas(disponibles) == {IFS: T0 + timedelta(hours=12), AIFS: T0}
    assert m1.corrida_ancla(disponibles) == IFS


def test_ancla_es_aifs_si_es_mas_reciente_e_ifs_si_empatan() -> None:
    assert m1.corrida_ancla({IFS: T0, AIFS: T0 + timedelta(hours=6)}) == AIFS
    assert m1.corrida_ancla({IFS: T0, AIFS: T0}) == IFS
    assert m1.corrida_ancla({GEFS: T0}) is None


# --- Representatividad de la celda -------------------------------------------------------


@pytest.mark.parametrize(
    ("capital", "celdas", "esperado"),
    [
        (12, [0.0], True),  # celda de mar
        (44, [43.0, 27.0, 47.0], False),
        (100, [400.0], False),  # costa: 300 m justos
        (100, [401.0], True),
        (2703, [2901.0, 3203.0], False),  # sierra: 500 m justos
        (2703, [3204.0], True),
        (2703, [None], False),
        (500, [1000.0], True),
    ],
)
def test_mal_representado(capital: int, celdas: list[float | None], esperado: bool) -> None:
    assert m1.mal_representado(capital, celdas) is esperado
