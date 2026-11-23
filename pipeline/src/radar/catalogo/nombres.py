"""Nombres con su ortografía a partir de los nombres del INEI (mayúsculas, sin tildes).

Las letras, los espacios y los guiones los pone siempre el INEI. De otra fuente
(Wikidata, GeoNames) solo se copian las tildes, y únicamente si su nombre, sin
tildes ni guiones y en mayúsculas, coincide exactamente con el del INEI. Si
ningún candidato coincide se usa el nombre del INEI en formato título, sin
añadir tildes, y el nombre se informa como no confirmado.
"""

import re
import unicodedata
from collections.abc import Iterable
from typing import NamedTuple

PARTICULAS = frozenset({"de", "del", "la", "las", "los", "el", "y", "e"})
"""Palabras que van en minúscula salvo al comienzo del nombre o tras un paréntesis."""

_PREFIJOS = re.compile(
    r"^(distrito|provincia|departamento|regi[oó]n|centro poblado)\s+(de\s+)?", re.IGNORECASE
)
_ACLARACION_FINAL = re.compile(r"\s*\([^()]*\)$")
_MARCAS_QUE_SE_QUITAN = frozenset({"́", "̀", "̈"})
"""Tilde aguda, grave y diéresis. La virgulilla de la ñ (U+0303) se conserva."""


def sin_tildes(texto: str) -> str:
    """Quita tildes y diéresis y conserva la ñ."""
    descompuesto = unicodedata.normalize("NFD", texto)
    limpio = "".join(c for c in descompuesto if c not in _MARCAS_QUE_SE_QUITAN)
    return unicodedata.normalize("NFC", limpio)


def _espaciado(texto: str) -> str:
    return " ".join(unicodedata.normalize("NFC", texto).replace("-", " ").split())


def clave(texto: str) -> str:
    """Forma comparable con un nombre del INEI: sin tildes ni guiones y en mayúsculas."""
    return _espaciado(sin_tildes(texto)).upper()


def limpiar_etiqueta(etiqueta: str, nombre_inei: str = "") -> str:
    """Quita "Distrito de", "Provincia de" o una aclaración final "(Perú)" de una etiqueta.

    La aclaración entre paréntesis se conserva si el propio nombre del INEI la lleva.
    """
    texto = " ".join(etiqueta.split())
    if "(" not in nombre_inei:
        texto = _ACLARACION_FINAL.sub("", texto)
    return _PREFIJOS.sub("", texto).strip()


def titulo(nombre: str) -> str:
    """``"SAN JUAN DE LA VIRGEN"`` → ``"San Juan de la Virgen"``, sin inventar tildes."""
    palabras = " ".join(nombre.split()).lower().split(" ")
    resultado: list[str] = []
    for i, palabra in enumerate(palabras):
        abre = palabra.startswith("(")
        nucleo = palabra[1:] if abre else palabra
        if i > 0 and not abre and nucleo in PARTICULAS:
            resultado.append(palabra)
        else:
            resultado.append(("(" if abre else "") + nucleo[:1].upper() + nucleo[1:])
    return " ".join(resultado)


def _copiar_tildes(base: str, modelo: str) -> str:
    """Pone en ``base`` las tildes de ``modelo`` (misma longitud, mismas letras)."""
    letras: list[str] = []
    for b, m in zip(base, modelo, strict=True):
        if m != sin_tildes(m) and sin_tildes(m).lower() == b.lower():
            letras.append(m.upper() if b.isupper() else m.lower())
        else:
            letras.append(b)
    return "".join(letras)


class Ortografia(NamedTuple):
    nombre: str
    confirmado: bool
    """Algún candidato coincide con el nombre del INEI."""
    descartadas: tuple[str, ...]
    """Otras formas con tildes distintas que también coincidían (fuentes en desacuerdo)."""


def con_tildes(nombre_inei: str, candidatos: Iterable[str]) -> Ortografia:
    """Nombre con ortografía a partir de los candidatos que coinciden con el del INEI.

    Entre los candidatos que coinciden se prefiere el primero que lleva tildes: que
    una fuente omita una tilde es mucho más común que que la invente. Las
    mayúsculas siguen siempre la norma de ``titulo``.
    """
    base = titulo(nombre_inei)
    objetivo = clave(nombre_inei)
    formas: list[str] = []
    for candidato in candidatos:
        limpio = _espaciado(limpiar_etiqueta(candidato, nombre_inei))
        if limpio and clave(limpio) == objetivo and len(limpio) == len(base):
            forma = _copiar_tildes(base, limpio)
            if forma not in formas:
                formas.append(forma)
    if not formas:
        return Ortografia(base, False, ())
    con_tilde = [f for f in formas if f != base]
    elegida = con_tilde[0] if con_tilde else base
    return Ortografia(elegida, True, tuple(con_tilde[1:]))
