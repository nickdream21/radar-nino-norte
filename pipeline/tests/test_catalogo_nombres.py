import pytest

from radar.catalogo.nombres import clave, con_tildes, limpiar_etiqueta, sin_tildes, titulo


def test_sin_tildes_conserva_la_enie() -> None:
    assert sin_tildes("Ferreñafe Óñez Güimar") == "Ferreñafe Oñez Guimar"


def test_clave_ignora_tildes_guiones_y_mayusculas() -> None:
    assert clave("  Chancay-Baños ") == clave("CHANCAY BAÑOS") == "CHANCAY BAÑOS"


@pytest.mark.parametrize(
    ("inei", "esperado"),
    [
        ("SAN JUAN DE LA VIRGEN", "San Juan de la Virgen"),
        ("LA LIBERTAD", "La Libertad"),
        ("SAN LUCAS (PUEBLO NUEVO DE COLAN)", "San Lucas (Pueblo Nuevo de Colan)"),
        ("Y", "Y"),
    ],
)
def test_titulo(inei: str, esperado: str) -> None:
    assert titulo(inei) == esperado


@pytest.mark.parametrize(
    ("etiqueta", "inei", "esperado"),
    [
        ("Distrito de El Tallán", "", "El Tallán"),
        ("provincia de Trujillo", "", "Trujillo"),
        ("Región Piura", "", "Piura"),
        ("Santa Cruz (Perú)", "SANTA CRUZ", "Santa Cruz"),
        ("Chimuch (Cortegana)", "CHIMUCH (CORTEGANA)", "Chimuch (Cortegana)"),
    ],
)
def test_limpiar_etiqueta(etiqueta: str, inei: str, esperado: str) -> None:
    assert limpiar_etiqueta(etiqueta, inei) == esperado


def test_copia_solo_las_tildes_de_un_candidato_que_coincide() -> None:
    ortografia = con_tildes("EL TALLAN", ["Distrito de El Tallán"])

    assert ortografia == ("El Tallán", True, ())


def test_prefiere_el_candidato_con_tildes() -> None:
    assert con_tildes("HUASMIN", ["Huasmin", "Huasmín"]).nombre == "Huasmín"


def test_candidato_con_otras_letras_no_cuenta() -> None:
    # "Tambogrande" (Wikidata) no tiene el espacio de "TAMBO GRANDE" (INEI).
    ortografia = con_tildes("TAMBO GRANDE", ["Tambogrande", "Távara"])

    assert ortografia == ("Tambo Grande", False, ())


def test_guion_del_inei_se_respeta() -> None:
    assert (
        con_tildes("SAN JOSE DE LOURDES", ["San José-de Lourdes"]).nombre == "San José de Lourdes"
    )


def test_fuentes_en_desacuerdo_se_informan() -> None:
    ortografia = con_tildes("CALLAYUC", ["Callayúc", "Cállayuc"])

    assert ortografia.nombre == "Callayúc"
    assert ortografia.descartadas == ("Cállayuc",)


def test_mayusculas_siguen_la_norma_aunque_el_candidato_no() -> None:
    assert con_tildes("SAN JOSE DE LA ESPERANZA", ["SAN JOSÉ DE LA ESPERANZA"]).nombre == (
        "San José de la Esperanza"
    )
