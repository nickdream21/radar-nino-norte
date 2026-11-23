import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from radar.cli import DATOS_ESTATICOS
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.enfen import FuenteEnfenEstatica
from tests.ayudas import AHORA, ahora_fijo

VALIDO = {
    "estado": "Alerta de El Niño Costero",
    "numero": "20-2026",
    "fecha": "2026-11-13T00:00:00-05:00",
    "enlace": "https://enfen.imarpe.gob.pe/",
}


def _archivo(tmp_path: Path, contenido: object) -> Path:
    ruta = tmp_path / "enfen.json"
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_archivo_del_repositorio_es_valido() -> None:
    bloque = FuenteEnfenEstatica(DATOS_ESTATICOS / "enfen.json", ahora=ahora_fijo).obtener()

    assert bloque.comunicado.numero
    assert bloque.fecha_dato == bloque.comunicado.fecha
    assert bloque.fecha_dato.tzinfo is UTC


def test_fecha_se_guarda_en_utc(tmp_path: Path) -> None:
    fuente = FuenteEnfenEstatica(_archivo(tmp_path, VALIDO), ahora=ahora_fijo)

    bloque = fuente.obtener()

    assert bloque.comunicado.fecha == datetime(2026, 11, 13, 5, tzinfo=UTC)
    assert bloque.obtenido_en == AHORA
    assert bloque.url == VALIDO["enlace"]
    assert fuente.id == "enfen-estatico"


@pytest.mark.parametrize(
    "contenido",
    [
        VALIDO | {"fecha": "2026-11-13T00:00:00"},  # sin zona horaria
        VALIDO | {"fecha": "2026-11-13"},
        VALIDO | {"numero": "veinte"},
        VALIDO | {"enlace": "enfen.gob.pe"},
        VALIDO | {"estado": ""},
        VALIDO | {"categoria": "fuerte"},
        {k: v for k, v in VALIDO.items() if k != "estado"},
        "<html>no es json</html>",
    ],
)
def test_archivo_invalido(tmp_path: Path, contenido: object) -> None:
    with pytest.raises(FuenteNoDisponible, match="no es válido"):
        FuenteEnfenEstatica(_archivo(tmp_path, contenido)).obtener()


def test_archivo_ausente(tmp_path: Path) -> None:
    with pytest.raises(FuenteNoDisponible, match="no se pudo leer"):
        FuenteEnfenEstatica(tmp_path / "no-existe.json").obtener()
