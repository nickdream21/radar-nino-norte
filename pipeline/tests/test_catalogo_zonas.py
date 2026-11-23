import pytest

from radar.catalogo.zonas import DatosZona, motivos_revision, zona
from radar.contratos.distritos import Vertiente, Zona


def _datos(
    altitud_m: int,
    distancia_costa_km: float = 20.0,
    vertiente: Vertiente = "pacifico",
    ubigeo: str = "200101",
    distancia_divisoria_km: float = 100.0,
) -> DatosZona:
    return DatosZona(
        ubigeo=ubigeo,
        altitud_m=altitud_m,
        vertiente=vertiente,
        distancia_costa_km=distancia_costa_km,
        distancia_divisoria_km=distancia_divisoria_km,
    )


@pytest.mark.parametrize(
    ("datos", "esperada"),
    [
        (_datos(30), "A"),
        (_datos(199, distancia_costa_km=60.0), "A"),
        (_datos(150, distancia_costa_km=60.1), "B"),
        (_datos(200), "B"),
        (_datos(999), "B"),
        (_datos(1000), "C"),
        (_datos(3000), "C"),
        (_datos(3001), "D"),
        # Marañón a cualquier altitud.
        (_datos(450, vertiente="atlantico"), "D"),
        # Todo Tumbes es B, también en la orilla.
        (_datos(5, ubigeo="240101"), "B"),
        (_datos(5, ubigeo="240101", vertiente="atlantico"), "D"),
    ],
)
def test_regla(datos: DatosZona, esperada: Zona) -> None:
    assert zona(datos) == esperada


def test_distrito_claro_no_se_marca() -> None:
    assert motivos_revision(_datos(30)) == []
    assert motivos_revision(_datos(2000)) == []


@pytest.mark.parametrize(
    ("datos", "fragmento"),
    [
        (_datos(235), "con 150 m sería zona A"),
        (_datos(173), "con 250 m sería zona B"),
        (_datos(931), "con 1100 m sería zona C"),
        (_datos(3009), "con 2850 m sería zona C"),
        (_datos(2969), "con 3150 m sería zona D"),
        (_datos(160, distancia_costa_km=68.0), "con 50 km sería zona A"),
        (_datos(55, distancia_costa_km=50.3), "con 70 km sería zona B"),
        (_datos(2166, distancia_divisoria_km=0.1), "en la otra vertiente sería zona D"),
    ],
)
def test_casos_fronterizos_se_marcan(datos: DatosZona, fragmento: str) -> None:
    assert any(fragmento in motivo for motivo in motivos_revision(datos))


def test_sierra_entre_2500_y_3000_en_el_pacifico_se_marca() -> None:
    motivos = motivos_revision(_datos(2718))

    assert zona(_datos(2718)) == "C"
    assert any("más de 2500 m" in motivo for motivo in motivos)


def test_cerca_de_un_umbral_pero_sin_cambio_de_zona_no_se_marca() -> None:
    # En el Atlántico la altitud no decide: siempre D.
    assert motivos_revision(_datos(1020, vertiente="atlantico")) == []
    # En Tumbes tampoco, mientras siga en el Pacífico y por debajo de 1000 m.
    assert motivos_revision(_datos(190, ubigeo="240101", distancia_costa_km=58.0)) == []


def test_divisoria_cercana_sin_efecto_no_se_marca() -> None:
    # Por encima de 3000 m es D en cualquiera de las dos vertientes.
    assert motivos_revision(_datos(3400, distancia_divisoria_km=1.0)) == []
