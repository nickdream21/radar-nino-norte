from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from radar.cli import DATOS_ESTATICOS
from radar.contratos import (
    BloqueEnfen,
    BloqueIcen,
    BloqueIndicesSemanales,
    BloqueMarPaita,
    EstadoNino,
    IndiceSemanal,
    ValorSemanal,
)
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.crw_erddap import FuenteCrwMarPaita
from radar.fuentes.enfen import FuenteEnfenEstatica
from radar.fuentes.igp_icen import FuenteIgpIcen
from radar.fuentes.noaa_cpc import FuenteNoaaCpcSemanal
from radar.publicacion import FuentesNino, publicar_estado_nino
from radar.publicacion.nino import ID_PRODUCTO, RUTA_ESTADO, VIGENCIA_MIN
from tests.ayudas import AHORA, CPC, CRW, ICEN, ahora_fijo, leer_fixture

MAS_TARDE = AHORA + timedelta(days=1)

SEMANAL = FuenteNoaaCpcSemanal(ahora=ahora_fijo).interpretar(leer_fixture(CPC))
ICEN_BLOQUE = FuenteIgpIcen(ahora=ahora_fijo).interpretar(leer_fixture(ICEN))
MAR = FuenteCrwMarPaita(ahora=ahora_fijo).interpretar(leer_fixture(CRW))
ENFEN = FuenteEnfenEstatica(DATOS_ESTATICOS / "enfen.json", ahora=ahora_fijo).obtener()


class FuenteFija[T]:
    """Fuente de prueba que devuelve un valor fijo o falla."""

    def __init__(self, valor: T | None = None, error: Exception | None = None) -> None:
        self._valor = valor
        self._error = error

    @property
    def id(self) -> str:
        return "fija"

    def obtener(self) -> T:
        if self._error is not None:
            raise self._error
        assert self._valor is not None
        return self._valor


def _caida[T]() -> FuenteFija[T]:
    return FuenteFija(error=FuenteNoDisponible("prueba", "caída"))


def _fuentes(
    semanal: FuenteFija[BloqueIndicesSemanales] | None = None,
    icen: FuenteFija[BloqueIcen] | None = None,
    mar: FuenteFija[BloqueMarPaita] | None = None,
    enfen: FuenteFija[BloqueEnfen] | None = None,
) -> FuentesNino:
    return FuentesNino(
        indices_semanales=semanal or FuenteFija(SEMANAL),
        icen=icen or FuenteFija(ICEN_BLOQUE),
        mar_paita=mar or FuenteFija(MAR),
        enfen=enfen or FuenteFija(ENFEN),
    )


def _todas_caidas() -> FuentesNino:
    return _fuentes(_caida(), _caida(), _caida(), _caida())


def _leer(carpeta: Path) -> EstadoNino:
    return EstadoNino.model_validate_json((carpeta / RUTA_ESTADO).read_text(encoding="utf-8"))


def test_publica_todos_los_bloques(tmp_path: Path) -> None:
    producto = publicar_estado_nino(tmp_path, _fuentes(), AHORA)

    assert producto is not None
    assert producto.id == ID_PRODUCTO
    assert producto.ruta == RUTA_ESTADO
    assert producto.vigencia_min == VIGENCIA_MIN
    assert producto.actualizado_en == MAR.fecha_dato  # el dato más reciente
    assert producto.fuente.split("; ") == [
        SEMANAL.fuente,
        ICEN_BLOQUE.fuente,
        MAR.fuente,
        ENFEN.fuente,
    ]
    estado = _leer(tmp_path)
    assert estado.generado_en == AHORA
    assert estado.indices_semanales == SEMANAL
    assert estado.icen == ICEN_BLOQUE
    assert estado.mar_paita == MAR
    assert estado.enfen == ENFEN


def test_fuente_caida_sin_anterior_publica_el_bloque_ausente(tmp_path: Path) -> None:
    producto = publicar_estado_nino(tmp_path, _fuentes(icen=_caida()), AHORA)

    assert producto is not None
    estado = _leer(tmp_path)
    assert estado.icen is None
    assert estado.indices_semanales == SEMANAL
    assert ICEN_BLOQUE.fuente not in producto.fuente


def test_fuente_caida_conserva_el_bloque_anterior(tmp_path: Path) -> None:
    publicar_estado_nino(tmp_path, _fuentes(), AHORA)

    publicar_estado_nino(tmp_path, _fuentes(mar=_caida()), MAS_TARDE)

    estado = _leer(tmp_path)
    assert estado.generado_en == MAS_TARDE
    assert estado.mar_paita == MAR
    # obtenido_en anterior a generado_en indica a la web que el bloque se conservó.
    assert estado.mar_paita is not None
    assert estado.mar_paita.obtenido_en == AHORA


def test_dato_que_no_cumple_el_contrato_aisla_solo_su_bloque(tmp_path: Path) -> None:
    try:
        ValorSemanal(fecha=AHORA, temperatura=float("nan"), anomalia=0)
    except ValidationError as error:
        invalido = error
    publicar_estado_nino(tmp_path, _fuentes(semanal=FuenteFija(error=invalido)), AHORA)

    estado = _leer(tmp_path)
    assert estado.indices_semanales is None
    assert estado.icen == ICEN_BLOQUE


def test_todas_caidas_sin_anterior_no_publica(tmp_path: Path) -> None:
    assert publicar_estado_nino(tmp_path, _todas_caidas(), AHORA) is None
    assert not (tmp_path / RUTA_ESTADO).exists()


def test_todas_caidas_con_anterior_republica_lo_anterior(tmp_path: Path) -> None:
    publicar_estado_nino(tmp_path, _fuentes(), AHORA)

    producto = publicar_estado_nino(tmp_path, _todas_caidas(), MAS_TARDE)

    assert producto is not None
    assert producto.actualizado_en == MAR.fecha_dato
    estado = _leer(tmp_path)
    assert estado.generado_en == MAS_TARDE
    assert [b.obtenido_en for b in estado.bloques()] == [AHORA] * 4


@pytest.mark.parametrize("contenido", ["{roto", '{"version_esquema": 99}'])
def test_anterior_invalido_no_se_reutiliza(tmp_path: Path, contenido: str) -> None:
    ruta = tmp_path / RUTA_ESTADO
    ruta.parent.mkdir(parents=True)
    ruta.write_text(contenido, encoding="utf-8")

    assert publicar_estado_nino(tmp_path, _todas_caidas(), AHORA) is None


def test_contrato_rechaza_serie_desordenada_o_ultimo_distinto() -> None:
    a = ValorSemanal(fecha=datetime(2026, 11, 4, tzinfo=UTC), temperatura=27, anomalia=5)
    b = ValorSemanal(fecha=datetime(2026, 11, 11, tzinfo=UTC), temperatura=27, anomalia=5)

    with pytest.raises(ValidationError, match="cronológico"):
        IndiceSemanal(ultimo=a, serie=[b, a])
    with pytest.raises(ValidationError, match="último valor"):
        IndiceSemanal(ultimo=a, serie=[a, b])


def test_contrato_exige_fechas_con_zona() -> None:
    with pytest.raises(ValidationError):
        ValorSemanal(fecha=datetime(2026, 11, 4), temperatura=27, anomalia=5)  # noqa: DTZ001
