"""Pruebas sobre el archivo confirmado ``datos-estaticos/distritos.json``."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from radar.catalogo import CatalogoInvalido, cargar_catalogo, zona_segun_regla
from radar.catalogo.cargar import NOMBRE_ARCHIVO
from radar.catalogo.resumen import ejemplos_discrepantes
from radar.cli import DATOS_ESTATICOS
from radar.contratos import CatalogoDistritos

RUTA = DATOS_ESTATICOS / NOMBRE_ARCHIVO
DISTRITOS_POR_DEPARTAMENTO = {
    "Cajamarca": 127,
    "La Libertad": 84,  # incluye Alto Trujillo (130112), creado por la Ley 31644 de 2022
    "Lambayeque": 38,
    "Piura": 65,
    "Tumbes": 13,
}
# Caja amplia del norte del Perú: ninguna capital puede caer fuera.
LATITUD = (-9.5, -3.3)
LONGITUD = (-81.4, -76.5)


@pytest.fixture(scope="module")
def catalogo() -> CatalogoDistritos:
    return cargar_catalogo(RUTA)


def test_ubigeos_unicos_y_bien_formados(catalogo: CatalogoDistritos) -> None:
    ubigeos = [d.ubigeo for d in catalogo.distritos]

    assert len(ubigeos) == len(set(ubigeos))
    assert all(re.fullmatch(r"(06|13|14|20|24)\d{4}", u) for u in ubigeos)
    assert all(not u.endswith("00") and u[2:4] != "00" for u in ubigeos)


def test_distritos_por_departamento(catalogo: CatalogoDistritos) -> None:
    cuenta = Counter(d.departamento for d in catalogo.distritos)

    assert cuenta == DISTRITOS_POR_DEPARTAMENTO
    assert sum(cuenta.values()) == 327


def test_capitales_dentro_de_la_region(catalogo: CatalogoDistritos) -> None:
    fuera = [
        d.ubigeo
        for d in catalogo.distritos
        if not (LATITUD[0] <= d.capital.latitud <= LATITUD[1])
        or not (LONGITUD[0] <= d.capital.longitud <= LONGITUD[1])
    ]

    assert fuera == []


def test_altitudes_plausibles(catalogo: CatalogoDistritos) -> None:
    for distrito in catalogo.distritos:
        altitud = distrito.capital.altitud_m
        assert 0 <= altitud <= 4200, distrito.ubigeo
        if distrito.departamento == "Tumbes":
            assert altitud < 300, distrito.ubigeo
    por_ubigeo = {d.ubigeo: d.capital.altitud_m for d in catalogo.distritos}
    # Referencias conocidas: Cajamarca ~2700 m, Piura y Trujillo a pocas decenas.
    assert 2600 <= por_ubigeo["060101"] <= 2800
    assert por_ubigeo["200101"] < 100
    assert por_ubigeo["130101"] < 100


def test_cada_provincia_en_un_solo_departamento(catalogo: CatalogoDistritos) -> None:
    departamentos: defaultdict[str, set[str]] = defaultdict(set)
    nombres: defaultdict[str, set[str]] = defaultdict(set)
    for distrito in catalogo.distritos:
        departamentos[distrito.provincia].add(distrito.departamento)
        nombres[distrito.ubigeo[:4]].add(distrito.provincia)

    assert {p: d for p, d in departamentos.items() if len(d) != 1} == {}
    assert {c: n for c, n in nombres.items() if len(n) != 1} == {}


def test_zona_igual_a_la_regla(catalogo: CatalogoDistritos) -> None:
    assert [d.ubigeo for d in catalogo.distritos if d.zona != zona_segun_regla(d)] == []
    assert set(Counter(d.zona for d in catalogo.distritos)) == {"A", "B", "C", "D"}


# Zonas tras la revisión del meteorólogo (regla de zonas.py), distrito por distrito.
ZONAS_REVISADAS: dict[str, str] = {
    # De C a D: cuenca del Santa.
    "131002": "D",  # Angasmarca
    "131003": "D",  # Cachicadán
    "131005": "D",  # Mollepata
    "131007": "D",  # Santa Cruz de Chuca
    # De D a C: vertiente atlántica por debajo de 1500 m.
    "060603": "C",  # Choros
    "060615": "C",  # Toribio Casanova
    "060801": "C",  # Jaén
    "060802": "C",  # Bellavista
    "060805": "C",  # Huabal
    "060807": "C",  # Pomahuaca
    "060808": "C",  # Pucará
    "060811": "C",  # San José del Alto
    "060812": "C",  # Santa Rosa
    "060901": "C",  # San Ignacio
    "060903": "C",  # Huarango
    "060904": "C",  # La Coipa
    "060905": "C",  # Namballe
    "060906": "C",  # San José de Lourdes
    "130807": "C",  # Ongón
    # De B a A: valles por debajo de 1000 m cerca del mar o al sur de -6,75°.
    "200702": "A",  # El Alto
    "140110": "A",  # Oyotún
    "061108": "A",  # Nanchoc
    "060508": "A",  # Yonán
    "060502": "A",  # Chilete
    "130201": "A",  # Ascope
    "130108": "A",  # Poroto
    "130110": "A",  # Simbal
    # De B a C: zonas forzadas (ladera húmeda).
    "061102": "C",  # Bolívar
    "061106": "C",  # La Florida
    "200305": "C",  # Lalaquiz
    # Sin cambio.
    "140102": "B",  # Chongoyape
    "140310": "B",  # Salas
    "200607": "A",  # Querecotillo
    "200304": "C",  # Huarmaca
    "060409": "C",  # Huambos
    "060702": "C",  # Chugur
    "061310": "C",  # Uticyacu
    "060410": "D",  # Lajas
}


def test_zonas_revisadas_por_el_meteorologo(catalogo: CatalogoDistritos) -> None:
    por_ubigeo = {d.ubigeo: d for d in catalogo.distritos}

    assert {u: por_ubigeo[u].zona for u in ZONAS_REVISADAS} == ZONAS_REVISADAS
    assert Counter(d.zona for d in catalogo.distritos) == {"A": 99, "B": 30, "C": 81, "D": 117}
    # Fuera del Santa, la sierra del Pacífico entre 2500 y 3000 m sigue en C.
    sierra = [
        d
        for d in catalogo.distritos
        if d.vertiente == "pacifico" and 2500 < d.capital.altitud_m <= 3000
    ]
    assert Counter(d.zona for d in sierra if d.cuenca != "Cuenca Santa") == {"C": 17}


def test_ejemplos_de_la_tabla_y_todo_tumbes(catalogo: CatalogoDistritos) -> None:
    assert ejemplos_discrepantes(catalogo) == []


def test_nombres_con_ortografia_oficial(catalogo: CatalogoDistritos) -> None:
    por_ubigeo = {d.ubigeo: d for d in catalogo.distritos}

    assert por_ubigeo["060801"].nombre == "Jaén"
    assert por_ubigeo["140201"].provincia == "Ferreñafe"
    assert por_ubigeo["130807"].nombre == "Ongón"
    assert all(d.nombre == d.nombre.strip() and d.nombre[0].isupper() for d in catalogo.distritos)


def test_todas_las_fuentes_atribuidas(catalogo: CatalogoDistritos) -> None:
    campos = " ".join(f.campos for f in catalogo.fuentes)

    for campo in (
        "ubigeo",
        "capital.latitud",
        "capital.altitud_m",
        "vertiente",
        "distancia_costa_km",
    ):
        assert campo in campos
    assert all(f.licencia and f.atribucion for f in catalogo.fuentes)


def test_dudosos_marcados(catalogo: CatalogoDistritos) -> None:
    revisar = {d.ubigeo for d in catalogo.distritos if d.revisar}

    # Alto Trujillo (ubicado con GeoNames), Huarmaca (junto a la divisoria), las zonas
    # forzadas y los que el meteorólogo pidió contrastar con percentiles.
    assert {"130112", "200304", "061102", "061106", "200305", "140102", "240203"} <= revisar
    assert not any("texto de la tabla" in m for d in catalogo.distritos for m in d.revisar)


def test_zona_alterada_se_rechaza(tmp_path: Path) -> None:
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    piura = next(d for d in datos["distritos"] if d["ubigeo"] == "200101")
    piura["zona"] = "D"
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(CatalogoInvalido, match="200101 Piura: guardada D, regla A"):
        cargar_catalogo(ruta)


def test_archivo_que_no_cumple_el_contrato(tmp_path: Path) -> None:
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    datos["distritos"][0]["capital"]["latitud"] = None
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(CatalogoInvalido, match="no cumple el contrato"):
        cargar_catalogo(ruta)


def test_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(CatalogoInvalido, match="no se pudo leer"):
        cargar_catalogo(tmp_path / NOMBRE_ARCHIVO)
