import pytest

from radar.catalogo.zonas import (
    CUENCA_SANTA,
    ZONAS_FORZADAS,
    DatosZona,
    ZonaForzada,
    motivos_revision,
    zona,
    zona_por_regla,
)
from radar.contratos.distritos import Vertiente, Zona


def _datos(
    altitud_m: int,
    distancia_costa_km: float = 30.0,
    vertiente: Vertiente = "pacifico",
    ubigeo: str = "200101",
    distancia_divisoria_km: float = 100.0,
    latitud: float = -5.2,
    cuenca: str = "Cuenca Piura",
) -> DatosZona:
    return DatosZona(
        ubigeo=ubigeo,
        altitud_m=altitud_m,
        vertiente=vertiente,
        cuenca=cuenca,
        distancia_costa_km=distancia_costa_km,
        latitud=latitud,
        distancia_divisoria_km=distancia_divisoria_km,
    )


@pytest.mark.parametrize(
    ("datos", "esperada"),
    [
        # 1. Vertiente atlántica: C por debajo de 1500 m, D desde ahí.
        (_datos(450, vertiente="atlantico"), "C"),
        (_datos(1499, vertiente="atlantico"), "C"),
        (_datos(1500, vertiente="atlantico"), "D"),
        (_datos(5, ubigeo="240101", vertiente="atlantico"), "C"),
        # 2. Todo Tumbes es B, también en la orilla y al sur de nada.
        (_datos(5, ubigeo="240101", distancia_costa_km=1.0), "B"),
        # 3. Cuenca del Santa en el Pacífico: D a cualquier altitud.
        (_datos(2600, cuenca=CUENCA_SANTA, latitud=-8.1), "D"),
        (_datos(800, cuenca=CUENCA_SANTA, latitud=-8.1), "D"),
        (_datos(1200, cuenca=CUENCA_SANTA, vertiente="atlantico"), "C"),
        # 4 y 5. Sierra del Pacífico.
        (_datos(3001), "D"),
        (_datos(3000), "C"),
        (_datos(2718), "C"),
        (_datos(1000), "C"),
        # 6. Costa y valles áridos: cerca del mar o al sur de -6,75°.
        (_datos(999, distancia_costa_km=19.9), "A"),
        (_datos(999, latitud=-6.76), "A"),
        (_datos(150, distancia_costa_km=80.0, latitud=-6.76), "A"),
        (_datos(999, distancia_costa_km=20.0, latitud=-6.75), "B"),
        # 7. Piedemonte.
        (_datos(200), "B"),
        (_datos(999), "B"),
        # 8 y 9. Llanura baja: interior a más de 60 km, costa el resto.
        (_datos(150, distancia_costa_km=60.1), "B"),
        (_datos(199, distancia_costa_km=60.0), "A"),
        (_datos(30), "A"),
    ],
)
def test_regla(datos: DatosZona, esperada: Zona) -> None:
    assert zona(datos) == esperada


def test_zonas_forzadas_explicitas_y_justificadas() -> None:
    # Bolívar, La Florida y Lalaquiz: ninguno más sin decisión del meteorólogo.
    assert {u: f.zona for u, f in ZONAS_FORZADAS.items()} == {
        "061102": "C",
        "061106": "C",
        "200305": "C",
    }
    assert all(isinstance(f, ZonaForzada) for f in ZONAS_FORZADAS.values())
    assert all("ladera húmeda" in f.motivo for f in ZONAS_FORZADAS.values())


def test_zona_forzada_gana_a_la_regla_y_se_explica() -> None:
    lalaquiz = _datos(969, ubigeo="200305", distancia_costa_km=95.0)

    assert zona_por_regla(lalaquiz) == "B"
    assert zona(lalaquiz) == "C"
    motivos = motivos_revision(lalaquiz)
    assert motivos[0].startswith("zona C fijada a mano (la regla daría B): ladera húmeda")
    # La altitud ya no decide nada: no se añade el motivo del umbral de 1000 m.
    assert not any("umbral" in m for m in motivos)


def test_distrito_claro_no_se_marca() -> None:
    assert motivos_revision(_datos(30)) == []
    assert motivos_revision(_datos(2000)) == []
    # Ya no se marca la sierra del Pacífico entre 2500 y 3000 m.
    assert motivos_revision(_datos(2718)) == []


@pytest.mark.parametrize(
    ("datos", "fragmento"),
    [
        (_datos(235), "con 150 m sería zona A"),
        (_datos(173), "con 250 m sería zona B"),
        (_datos(931), "con 1100 m sería zona C"),
        (_datos(931, latitud=-7.0), "con 1100 m sería zona C"),
        (_datos(3009), "con 2850 m sería zona C"),
        (_datos(2969), "con 3150 m sería zona D"),
        (_datos(160, distancia_costa_km=68.0), "con 50 km sería zona A"),
        (_datos(55, distancia_costa_km=50.3), "con 70 km sería zona B"),
        (_datos(2166, distancia_divisoria_km=0.1), "en la otra vertiente sería zona D"),
        (_datos(2000, distancia_divisoria_km=0.1, vertiente="atlantico"), "sería zona C"),
    ],
)
def test_casos_fronterizos_se_marcan(datos: DatosZona, fragmento: str) -> None:
    assert any(fragmento in motivo for motivo in motivos_revision(datos))


@pytest.mark.parametrize(
    ("altitud_m", "fragmento"),
    [
        (1370, "umbral de 1500 m (con 1650 m sería zona D)"),
        (1650, "umbral de 1500 m (con 1350 m sería zona C)"),
    ],
)
def test_margen_de_1500_m_en_el_atlantico(altitud_m: int, fragmento: str) -> None:
    motivos = motivos_revision(_datos(altitud_m, vertiente="atlantico"))

    assert any(fragmento in m for m in motivos)


def test_margen_de_1500_m_no_afecta_al_pacifico() -> None:
    assert motivos_revision(_datos(1500)) == []
    assert motivos_revision(_datos(1349, vertiente="atlantico")) == []


def test_revision_pendiente_pedida_por_el_meteorologo() -> None:
    for ubigeo in ("140102", "240203"):
        motivos = motivos_revision(_datos(212, ubigeo=ubigeo, distancia_costa_km=61.7))
        assert "pendiente de contraste con percentiles" in motivos


def test_cerca_de_un_umbral_pero_sin_cambio_de_zona_no_se_marca() -> None:
    # En el Atlántico solo cuenta el umbral de 1500 m.
    assert motivos_revision(_datos(1020, vertiente="atlantico")) == []
    assert motivos_revision(_datos(2950, vertiente="atlantico")) == []
    # En Tumbes tampoco, mientras siga en el Pacífico.
    assert motivos_revision(_datos(190, ubigeo="240101", distancia_costa_km=58.0)) == []
    # En el Santa la altitud no decide.
    assert motivos_revision(_datos(2950, cuenca=CUENCA_SANTA)) == []
    # Al sur de -6,75° no importa la distancia al mar.
    assert motivos_revision(_datos(160, distancia_costa_km=68.0, latitud=-7.0)) == []


def test_divisoria_cercana_sin_efecto_no_se_marca() -> None:
    # Por encima de 3000 m es D en cualquiera de las dos vertientes.
    assert motivos_revision(_datos(3400, distancia_divisoria_km=1.0)) == []
    # Entre 1000 y 1500 m es C en cualquiera de las dos vertientes.
    assert motivos_revision(_datos(1200, distancia_divisoria_km=1.0)) == []
