import copy
import gzip
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from radar.catalogo import cargar_catalogo
from radar.cli import DATOS_ESTATICOS, publicar
from radar.contratos import CatalogoDistritos, Manifiesto, ProductoPublicado
from radar.contratos.lluvia import ArchivoLluvia, DistritoLluvia, LluviaDistritos
from radar.fuentes import FuenteNoDisponible
from radar.fuentes.dias_12utc import primer_inicio_desde
from radar.fuentes.open_meteo_ensambles import (
    SISTEMAS,
    Celda,
    DiaLluvia,
    EnsamblesLluvia,
    LimitadorCuota,
    PronosticoSistema,
    Punto,
    SeriePunto,
    Sistema,
)
from radar.modelos import lluvia as m1
from radar.publicacion import FuentesNino
from radar.publicacion import lluvia as pub
from tests.ayudas import (
    OM_ENSAMBLE,
    OM_META,
    Esperas,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
)

IFS, AIFS, GEFS = Sistema.IFS, Sistema.AIFS, Sistema.GEFS
D0 = datetime(2026, 11, 23, 0, tzinfo=UTC)
D12 = D0 + timedelta(hours=12)
CORRIDAS_00 = {IFS: D0, AIFS: D0, GEFS: D0}
UBIGEOS = ("060101", "200101", "240101")  # Cajamarca (D), Piura (A), Tumbes (B)

Lluvia = Callable[[Sistema, datetime, str, int, int], float | None]
"""(sistema, inicialización, celda, día, miembro) -> mm."""


def ifs_mojado(sistema: Sistema, _: datetime, __: str, ___: int, ____: int) -> float:
    """IFS: 20 mm en todos los miembros; AIFS y GEFS secos."""
    return 20.0 if sistema is IFS else 0.0


@pytest.fixture(scope="module")
def catalogo_completo() -> CatalogoDistritos:
    return cargar_catalogo(DATOS_ESTATICOS / "distritos.json")


@pytest.fixture(scope="module")
def catalogo(catalogo_completo: CatalogoDistritos) -> CatalogoDistritos:
    distritos = [d for d in catalogo_completo.distritos if d.ubigeo in UBIGEOS]
    return catalogo_completo.model_copy(update={"distritos": distritos})


class ProveedorFalso:
    """Simula Open-Meteo: cuenta consultas de ``meta.json`` y descargas."""

    def __init__(
        self,
        puntos: Sequence[Punto],
        corridas: Mapping[Sistema, datetime | None],
        lluvia: Lluvia = ifs_mojado,
        *,
        fallan: frozenset[Sistema] = frozenset(),
        altitud: Callable[[Punto], float | None] = lambda _: 100.0,
    ) -> None:
        self.puntos = list(puntos)
        self.corridas = dict(corridas)
        self.lluvia = lluvia
        self.fallan = fallan
        self.altitud = altitud
        self.metas = 0
        self.descargas: list[list[Sistema]] = []

    def inicializacion(self, sistema: Sistema) -> datetime | None:
        self.metas += 1
        return self.corridas.get(sistema)

    def descargar(
        self, sistemas: Sequence[Sistema], conocidas: Mapping[Sistema, datetime]
    ) -> EnsamblesLluvia:
        self.descargas.append(list(sistemas))
        entregados = {s: self._pronostico(s) for s in sistemas if s not in self.fallan}
        fallos = {s: "caído" for s in sistemas if s in self.fallan}
        if not entregados:
            raise FuenteNoDisponible("falsa", "fallaron todos los sistemas")
        return EnsamblesLluvia(
            obtenido_en=ahora_fijo(), sistemas=entregados, fallos=fallos, sin_corrida_nueva={}
        )

    def _pronostico(self, sistema: Sistema) -> PronosticoSistema:
        inicio = self.corridas[sistema]
        assert inicio is not None
        primer = primer_inicio_desde(inicio)
        miembros = SISTEMAS[sistema].miembros
        series = []
        for punto in self.puntos:
            dias = []
            for k in range(7):
                valores = tuple(
                    self.lluvia(sistema, inicio, punto.id, k, i) for i in range(miembros)
                )
                dias.append(
                    DiaLluvia(
                        inicio=primer + timedelta(days=k),
                        lluvia_mm=valores,
                        miembros_validos=sum(v is not None for v in valores),
                    )
                )
            series.append(
                SeriePunto(
                    punto=punto,
                    celda=Celda(
                        latitud=punto.latitud,
                        longitud=punto.longitud,
                        altitud_m=self.altitud(punto),
                    ),
                    dias=tuple(dias),
                )
            )
        return PronosticoSistema(
            sistema=sistema,
            modelo=SISTEMAS[sistema].modelo,
            miembros=miembros,
            inicializacion=inicio,
            primer_dia=primer,
            puntos=tuple(series),
        )


def _proveedor(
    catalogo: CatalogoDistritos, corridas: Mapping[Sistema, datetime | None], **opciones: object
) -> ProveedorFalso:
    return ProveedorFalso(pub.puntos_catalogo(catalogo), corridas, **opciones)  # type: ignore[arg-type]


def _publicar(
    carpeta: Path, catalogo: CatalogoDistritos, proveedor: ProveedorFalso, hora: int = 13
) -> ProductoPublicado | None:
    ahora = D0 + timedelta(hours=hora)
    return pub.publicar_lluvia(carpeta, pub.FuentesLluvia(catalogo, proveedor), ahora)


def _producto(carpeta: Path) -> LluviaDistritos:
    return LluviaDistritos.model_validate_json((carpeta / pub.RUTA_PRODUCTO).read_bytes())


def _archivos(carpeta: Path) -> list[Path]:
    return sorted((carpeta / pub.CARPETA_ARCHIVO).glob("*.json.gz"))


def _distrito(producto: LluviaDistritos, ubigeo: str) -> DistritoLluvia:
    return next(d for d in producto.distritos if d.ubigeo == ubigeo)


# --- Primera ejecución -------------------------------------------------------------------


def test_primera_ejecucion_descarga_todo_y_publica(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo, CORRIDAS_00)

    entrada = _publicar(tmp_path, catalogo, proveedor)

    assert proveedor.descargas == [[IFS, AIFS, GEFS]]
    assert entrada is not None
    assert entrada.id == "lluvia-distritos"
    assert entrada.ruta == "lluvia/distritos.json"
    assert entrada.actualizado_en == D0
    assert entrada.vigencia_min == 30 * 60

    producto = _producto(tmp_path)
    assert producto.verificacion == "sin_verificar"
    assert [(c.sistema, c.peso) for c in producto.corridas] == [
        ("ecmwf_ifs", 0.5),
        ("ecmwf_aifs", 0.25),
        ("ncep_gefs", 0.25),
    ]
    assert [d.inicio for d in producto.dias] == [D12 + timedelta(days=k) for k in range(3)]
    assert producto.dias[0].fin == D12 + timedelta(days=1)
    assert producto.tendencia.inicio == D12 + timedelta(days=3)
    assert producto.tendencia.fin == D12 + timedelta(days=7)
    assert producto.metodo.umbrales_mm["A"].t1_mm == 5.0
    # IFS 20 mm, los demás secos: P = 50 % para todo umbral ≤ 20 mm.
    piura = _distrito(producto, "200101")  # zona A: 5/15/40
    assert [d.probabilidades for d in piura.dias] == [[50, 50, 0]] * 3
    assert [d.nivel for d in piura.dias] == [3, 3, 3]
    assert piura.tendencia == 3
    cajamarca = _distrito(producto, "060101")  # zona D: 10/20/40
    assert cajamarca.dias[0].probabilidades == [50, 50, 0]
    tumbes = _distrito(producto, "240101")  # zona B: 10/30/70
    assert tumbes.dias[0].probabilidades == [50, 0, 0]
    assert tumbes.dias[0].nivel == 2
    # Cajamarca (2 706 m) en una celda de 100 m: mal representada.
    assert cajamarca.mal_representado
    assert not piura.mal_representado
    assert piura.celda is not None
    assert producto.celdas[piura.celda].altitud_m == 100
    assert len(_archivos(tmp_path)) == 1
    assert (tmp_path / pub.RUTA_ESTADO).exists()


def test_hora_sin_corrida_nueva_no_descarga_ni_reescribe(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    antes = (tmp_path / pub.RUTA_PRODUCTO).read_bytes()
    estado = (tmp_path / pub.RUTA_ESTADO).read_bytes()

    proveedor = _proveedor(catalogo, CORRIDAS_00)
    entrada = _publicar(tmp_path, catalogo, proveedor, hora=14)

    assert proveedor.descargas == []
    assert proveedor.metas == 3
    assert (tmp_path / pub.RUTA_PRODUCTO).read_bytes() == antes
    assert (tmp_path / pub.RUTA_ESTADO).read_bytes() == estado
    assert len(_archivos(tmp_path)) == 1
    assert entrada is not None
    assert entrada.actualizado_en == D0


def test_corridas_fuera_del_plan_no_se_descargan(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    seis = D0 + timedelta(hours=6)

    proveedor = _proveedor(catalogo, {IFS: seis, AIFS: seis, GEFS: seis})
    _publicar(tmp_path, catalogo, proveedor, hora=15)

    assert proveedor.descargas == []


def test_llega_solo_ifs_de_12_utc(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))

    # La corrida de 12 UTC de IFS ya no ve lluvia.
    proveedor = _proveedor(catalogo, {IFS: D12, AIFS: D0, GEFS: D0}, lluvia=lambda *_: 0.0)
    entrada = _publicar(tmp_path, catalogo, proveedor, hora=24)

    assert proveedor.descargas == [[IFS]]
    producto = _producto(tmp_path)
    assert pub.corridas_de(producto) == {IFS: D12, AIFS: D0, GEFS: D0}
    # Mismos días: la corrida de 12 UTC empieza el mismo día pluviométrico.
    assert producto.dias[0].inicio == D12
    # IFS nuevo seco; AIFS y GEFS de 00 (lo guardado) también: 0 %.
    assert _distrito(producto, "200101").dias[0].probabilidades == [0, 0, 0]
    assert entrada is not None
    assert entrada.actualizado_en == D12
    archivos = _archivos(tmp_path)
    assert len(archivos) == 2
    archivo = pub.leer_archivo(archivos[-1])
    assert archivo.descargados == ["ecmwf_ifs"]
    assert [s.sistema for s in archivo.sistemas] == ["ecmwf_ifs", "ecmwf_aifs", "ncep_gefs"]
    assert archivo.sistemas[1].celdas[0].dias[0].lluvia_mm is None
    assert archivo.pronostico == producto


def test_mezcla_usa_los_conteos_guardados_de_los_otros_sistemas(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    def gefs_mojado(s: Sistema, inicio: datetime, celda: str, k: int, i: int) -> float:
        return 25.0 if s is GEFS else 0.0

    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00, lluvia=gefs_mojado))
    proveedor = _proveedor(catalogo, {IFS: D12, AIFS: D0, GEFS: D0}, lluvia=lambda *_: 0.0)
    _publicar(tmp_path, catalogo, proveedor, hora=24)

    # GEFS de 00 (guardado) con 25 mm: 25 % para T ≤ 25 mm; IFS 12 y AIFS secos.
    piura = _distrito(_producto(tmp_path), "200101")
    assert piura.dias[0].probabilidades == [25, 25, 0]


def test_falta_un_sistema_renormaliza_y_lo_declara(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo, CORRIDAS_00, fallan=frozenset({IFS}))

    _publicar(tmp_path, catalogo, proveedor)

    producto = _producto(tmp_path)
    assert [(c.sistema, c.peso) for c in producto.corridas] == [
        ("ecmwf_aifs", 0.5),
        ("ncep_gefs", 0.5),
    ]
    assert producto.dias[0].sistemas == ["ecmwf_aifs", "ncep_gefs"]


def test_solo_gefs_no_emite_pero_guarda_y_archiva(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo, CORRIDAS_00, fallan=frozenset({IFS, AIFS}))

    entrada = _publicar(tmp_path, catalogo, proveedor)

    assert entrada is None
    assert not (tmp_path / pub.RUTA_PRODUCTO).exists()
    archivo = pub.leer_archivo(_archivos(tmp_path)[0])
    assert archivo.pronostico is None
    assert archivo.descargados == ["ncep_gefs"]

    # Al llegar ECMWF se emite sin volver a descargar GEFS.
    segundo = _proveedor(catalogo, CORRIDAS_00)
    _publicar(tmp_path, catalogo, segundo, hora=14)
    assert segundo.descargas == [[IFS, AIFS]]
    assert len(_producto(tmp_path).corridas) == 3


def test_solo_gefs_conserva_el_producto_anterior(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    antes = (tmp_path / pub.RUTA_PRODUCTO).read_bytes()
    manana = D0 + timedelta(days=1)

    proveedor = _proveedor(
        catalogo, {IFS: manana, AIFS: manana, GEFS: manana}, fallan=frozenset({IFS, AIFS})
    )
    entrada = _publicar(tmp_path, catalogo, proveedor, hora=37)

    # GEFS está a 24 h de la última corrida ECMWF: no entra; el producto no cambia.
    assert (tmp_path / pub.RUTA_PRODUCTO).read_bytes() == antes
    assert entrada is not None
    assert entrada.actualizado_en == D0


def test_dia_sin_miembros_validos_queda_sin_nivel(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    def sin_dia_2(s: Sistema, inicio: datetime, celda: str, k: int, i: int) -> float | None:
        return None if k == 1 and s is not GEFS else 5.0

    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00, lluvia=sin_dia_2))

    piura = _distrito(_producto(tmp_path), "200101")
    assert piura.dias[1].nivel is None
    assert piura.dias[1].probabilidades is None
    assert piura.dias[0].probabilidades == [100, 0, 0]


def test_celda_de_mar_marca_mal_representado(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    tumbes = pub.id_nodo(-3.5669, -80.4515)
    proveedor = _proveedor(catalogo, CORRIDAS_00, altitud=lambda p: 0.0 if p.id == tumbes else 30.0)

    _publicar(tmp_path, catalogo, proveedor)

    producto = _producto(tmp_path)
    assert _distrito(producto, "240101").mal_representado
    assert not _distrito(producto, "200101").mal_representado


# --- Fallos ------------------------------------------------------------------------------


def test_open_meteo_caido_conserva_el_producto(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    antes = (tmp_path / pub.RUTA_PRODUCTO).read_bytes()

    proveedor = _proveedor(catalogo, dict.fromkeys(Sistema))
    entrada = _publicar(tmp_path, catalogo, proveedor, hora=40)

    assert proveedor.descargas == []
    assert (tmp_path / pub.RUTA_PRODUCTO).read_bytes() == antes
    assert entrada is not None
    assert entrada.actualizado_en == D0


def test_descarga_fallida_entera_conserva_el_producto(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    manana = {s: D0 + timedelta(days=1) for s in Sistema}

    proveedor = _proveedor(catalogo, manana, fallan=frozenset(Sistema))
    entrada = _publicar(tmp_path, catalogo, proveedor, hora=40)

    assert proveedor.descargas == [[IFS, AIFS, GEFS]]
    assert entrada is not None
    assert entrada.actualizado_en == D0
    assert len(_archivos(tmp_path)) == 1


def test_producto_corrupto_se_rehace_del_estado_sin_descargar(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    original = _producto(tmp_path)
    (tmp_path / pub.RUTA_PRODUCTO).write_text("{no es json", encoding="utf-8")

    proveedor = _proveedor(catalogo, CORRIDAS_00)
    entrada = _publicar(tmp_path, catalogo, proveedor)

    assert proveedor.descargas == []
    assert entrada is not None
    assert _producto(tmp_path) == original


def test_producto_y_estado_corruptos_vuelven_a_descargar(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    (tmp_path / pub.RUTA_PRODUCTO).write_text("[]", encoding="utf-8")
    (tmp_path / pub.RUTA_ESTADO).write_text("{}", encoding="utf-8")

    proveedor = _proveedor(catalogo, CORRIDAS_00)
    _publicar(tmp_path, catalogo, proveedor)

    assert proveedor.descargas == [[IFS, AIFS, GEFS]]


def test_estado_con_otros_umbrales_se_descarta(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    ruta = tmp_path / pub.RUTA_ESTADO
    estado = json.loads(ruta.read_text(encoding="utf-8"))
    estado["umbrales_conteo_mm"] = [1.0]
    ruta.write_text(json.dumps(estado), encoding="utf-8")

    assert pub.leer_estado(ruta) == {}


def test_sin_producto_anterior_ni_datos_no_publica(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo, dict.fromkeys(Sistema))

    assert _publicar(tmp_path, catalogo, proveedor) is None
    assert not (tmp_path / "lluvia").exists()


def test_corrida_sin_hora_confirmada_se_descarta(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo, CORRIDAS_00)
    original = proveedor._pronostico

    def sin_hora(sistema: Sistema) -> PronosticoSistema:
        p = original(sistema)
        return p.model_copy(update={"inicializacion": None}) if sistema is AIFS else p

    proveedor._pronostico = sin_hora  # type: ignore[method-assign]
    _publicar(tmp_path, catalogo, proveedor)

    assert [c.sistema for c in _producto(tmp_path).corridas] == ["ecmwf_ifs", "ncep_gefs"]
    with pytest.raises(ValueError, match="hora desconocida"):
        pub.archivar_sistema(sin_hora(AIFS), ahora_fijo())


# --- Plan de descarga --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sistema", "ultima", "conocida", "esperado"),
    [
        (IFS, D0, None, True),
        (IFS, D0 + timedelta(hours=6), None, True),  # sin dato: cualquier corrida
        (IFS, D0, D0, False),
        (IFS, D0 - timedelta(hours=6), D0, False),
        (IFS, D12, D0, True),
        (AIFS, D12, D0, False),
        (GEFS, D0 + timedelta(hours=18), D0, False),
        (GEFS, D0 + timedelta(hours=24), D0, True),
        (GEFS, D0 + timedelta(hours=30), D0, True),  # recuperación: más de 24 h atrás
        (AIFS, D0 + timedelta(hours=30), D0 + timedelta(hours=6), False),
    ],
)
def test_debe_descargar(
    sistema: Sistema, ultima: datetime, conocida: datetime | None, esperado: bool
) -> None:
    assert pub.debe_descargar(sistema, ultima, conocida) is esperado


def test_puntos_del_catalogo_deduplican_celdas(catalogo_completo: CatalogoDistritos) -> None:
    puntos = pub.puntos_catalogo(catalogo_completo)

    assert len(puntos) == 117
    assert len({p.id for p in puntos}) == 117
    assert pub.id_nodo(-5.1945, -80.6328) == "-5.25,-80.75"


# --- Archivo -----------------------------------------------------------------------------


def test_archivo_ida_y_vuelta_reproduce_las_probabilidades(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    def variada(s: Sistema, inicio: datetime, celda: str, k: int, i: int) -> float | None:
        if i == 3:
            return None
        return float((i * (k + 2) + len(celda) + list(Sistema).index(s) * 7) % 60)

    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00, lluvia=variada))
    archivo = pub.leer_archivo(_archivos(tmp_path)[0])
    publicado = _producto(tmp_path)
    assert archivo.pronostico == publicado

    # Rehacer desde los valores por miembro, sin usar los conteos guardados.
    umbrales = archivo.umbrales_conteo_mm
    pesos = {
        Sistema(s): Fraction(p).limit_denominator()
        for s, p in archivo.pronostico.metodo.pesos.items()
    }
    valores = {
        (Sistema(s.sistema), c.id, d.inicio): d.lluvia_mm
        for s in archivo.sistemas
        for c in s.celdas
        for d in c.dias
    }
    for distrito in catalogo.distritos:
        nid = pub.id_nodo(distrito.capital.latitud, distrito.capital.longitud)
        t = archivo.pronostico.metodo.umbrales_mm[distrito.zona]
        for k, dia in enumerate(archivo.pronostico.dias):
            esperado = []
            for umbral in (t.t1_mm, t.t2_mm, t.t3_mm):
                suma, peso = Fraction(0), Fraction(0)
                for sistema in Sistema:
                    miembros = [
                        v for v in valores[(sistema, nid, dia.inicio)] or [] if v is not None
                    ]
                    suma += pesos[sistema] * Fraction(
                        sum(v >= umbral for v in miembros), len(miembros)
                    )
                    peso += pesos[sistema]
                esperado.append(int(suma / peso * 100 + Fraction(1, 2)))
            assert umbrales == list(m1.UMBRALES_CONTEO_MM)
            obtenido = next(d for d in publicado.distritos if d.ubigeo == distrito.ubigeo)
            assert obtenido.dias[k].probabilidades == esperado


def test_archivo_es_reproducible_y_se_limita_lo_pendiente(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    archivo = pub.leer_archivo(_archivos(tmp_path)[0])
    carpeta = tmp_path / "otra"

    primero = pub.escribir_archivo(archivo, carpeta)
    contenido = primero.read_bytes()
    pub.escribir_archivo(archivo, carpeta)
    assert primero.read_bytes() == contenido  # gzip sin fecha
    assert primero.name == "lluvia-distritos-20261123T130000Z.json.gz"

    for h in range(pub.MAXIMO_PENDIENTES + 3):
        copia = archivo.model_copy(update={"generado_en": D0 + timedelta(days=1, hours=h)})
        pub.escribir_archivo(copia, carpeta)
    pendientes = sorted(carpeta.glob("*.json.gz"))
    assert len(pendientes) == pub.MAXIMO_PENDIENTES
    assert primero not in pendientes


def test_carpeta_de_archivo_configurable(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    fuentes = pub.FuentesLluvia(catalogo, _proveedor(catalogo, CORRIDAS_00))

    pub.publicar_lluvia(
        tmp_path / "pub", fuentes, D0, carpeta_archivo=tmp_path / "arch", commit="abc"
    )

    (ruta,) = (tmp_path / "arch").iterdir()
    assert pub.leer_archivo(ruta).commit == "abc"
    assert not (tmp_path / "pub" / pub.CARPETA_ARCHIVO).exists()


# --- Tamaño ------------------------------------------------------------------------------


def test_producto_completo_es_compacto(
    tmp_path: Path, catalogo_completo: CatalogoDistritos
) -> None:
    proveedor = _proveedor(catalogo_completo, CORRIDAS_00)

    _publicar(tmp_path, catalogo_completo, proveedor)

    producto = _producto(tmp_path)
    assert len(producto.distritos) == 327
    assert len(producto.celdas) == 117
    assert (tmp_path / pub.RUTA_PRODUCTO).stat().st_size < 120_000


# --- Integración con ``radar publicar`` --------------------------------------------------


class _Caida:
    id = "caida"

    def obtener(self) -> object:
        raise FuenteNoDisponible("caida", "sin red")


def _nino_caido() -> FuentesNino:
    return FuentesNino(_Caida(), _Caida(), _Caida(), _Caida())  # type: ignore[arg-type]


def test_publicar_lista_el_producto_conservado_con_su_fecha(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    fuentes = pub.FuentesLluvia(catalogo, _proveedor(catalogo, CORRIDAS_00))
    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=13), lluvia=fuentes)

    caido = pub.FuentesLluvia(catalogo, _proveedor(catalogo, dict.fromkeys(Sistema)))
    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=40), lluvia=caido)

    manifiesto = Manifiesto.model_validate_json((tmp_path / "manifiesto.json").read_bytes())
    (entrada,) = manifiesto.productos
    assert entrada.id == "lluvia-distritos"
    assert entrada.actualizado_en == D0
    assert manifiesto.generado_en == D0 + timedelta(hours=40)


def test_error_inesperado_en_lluvia_no_afecta_a_lo_demas(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    fuentes = pub.FuentesLluvia(catalogo, _proveedor(catalogo, CORRIDAS_00))
    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=13), lluvia=fuentes)

    class Roto(ProveedorFalso):
        def inicializacion(self, sistema: Sistema) -> datetime | None:
            raise RuntimeError("fallo de programación")

    roto = pub.FuentesLluvia(catalogo, Roto(pub.puntos_catalogo(catalogo), CORRIDAS_00))
    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=14), lluvia=roto)

    manifiesto = Manifiesto.model_validate_json((tmp_path / "manifiesto.json").read_bytes())
    assert [p.id for p in manifiesto.productos] == ["lluvia-distritos"]


def test_publicar_sin_fuentes_de_lluvia_conserva_el_anterior(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    fuentes = pub.FuentesLluvia(catalogo, _proveedor(catalogo, CORRIDAS_00))
    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=13), lluvia=fuentes)

    publicar(tmp_path, _nino_caido(), D0 + timedelta(hours=14))

    manifiesto = Manifiesto.model_validate_json((tmp_path / "manifiesto.json").read_bytes())
    assert [p.id for p in manifiesto.productos] == ["lluvia-distritos"]


# --- Proveedor real con respuestas grabadas ---------------------------------------------

CORTO = {IFS: "ifs", AIFS: "aifs", GEFS: "gefs"}
POR_MODELO = {SISTEMAS[s].modelo: s for s in Sistema}


def _api(pedidas: list[httpx.Request]) -> Callable[[httpx.Request], httpx.Response]:
    def manejador(request: httpx.Request) -> httpx.Response:
        pedidas.append(request)
        if request.url.path.startswith("/data/"):
            sistema = POR_MODELO[request.url.path.split("/")[2]]
            texto = leer_fixture(OM_META.format(sistema=CORTO[sistema]))
        else:
            sistema = POR_MODELO[request.url.params["models"]]
            texto = leer_fixture(OM_ENSAMBLE.format(sistema=CORTO[sistema]))
        return httpx.Response(200, text=texto, headers={"content-type": "application/json"})

    return manejador


def test_proveedor_open_meteo_con_respuestas_grabadas() -> None:
    pedidas: list[httpx.Request] = []
    proveedor = pub.ProveedorOpenMeteo(
        [
            Punto(id="-5.25,-80.75", latitud=-5.25, longitud=-80.75),
            Punto(id="-3.50,-80.50", latitud=-3.5, longitud=-80.5),
        ],
        cliente=cliente_simulado(_api(pedidas)),
        politica=politica_sin_espera(),
        limitador=LimitadorCuota(esperar=Esperas()),
        ahora=ahora_fijo,
    )

    inicio = proveedor.inicializacion(IFS)
    resultado = proveedor.descargar([IFS], {})

    assert inicio == D0
    assert list(resultado.sistemas) == [IFS]
    datos = [p for p in pedidas if not p.url.path.startswith("/data/")]
    assert len(datos) == 1
    archivado = pub.archivar_sistema(resultado.sistemas[IFS], ahora_fijo())
    assert archivado.celdas[0].dias[0].validos == 51


def test_fuentes_reales_usan_las_celdas_del_catalogo(
    catalogo_completo: CatalogoDistritos,
) -> None:
    fuentes = pub.fuentes_lluvia_reales(catalogo_completo)

    assert isinstance(fuentes.proveedor, pub.ProveedorOpenMeteo)
    assert fuentes.catalogo is catalogo_completo


def test_primera_ejecucion_acepta_corridas_fuera_del_plan(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    seis = D0 + timedelta(hours=6)
    proveedor = _proveedor(catalogo, {IFS: D0, AIFS: seis, GEFS: seis})

    _publicar(tmp_path, catalogo, proveedor, hora=15)

    assert proveedor.descargas == [[IFS, AIFS, GEFS]]
    assert pub.corridas_de(_producto(tmp_path)) == {IFS: D0, AIFS: seis, GEFS: seis}


def test_construir_sin_ecmwf_no_da_producto(tmp_path: Path, catalogo: CatalogoDistritos) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    estado = pub.leer_estado(tmp_path / pub.RUTA_ESTADO)

    assert pub.construir_producto(catalogo, {GEFS: estado[GEFS]}, D0) is None


# --- Contrato ----------------------------------------------------------------------------


@pytest.fixture
def producto_json(tmp_path: Path, catalogo: CatalogoDistritos) -> dict[str, Any]:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00))
    datos: dict[str, Any] = json.loads((tmp_path / pub.RUTA_PRODUCTO).read_text("utf-8"))
    return datos


def _invalido(datos: dict[str, Any], cambio: Callable[[dict[str, Any]], None]) -> None:
    copia = copy.deepcopy(datos)
    cambio(copia)
    with pytest.raises(ValidationError):
        LluviaDistritos.model_validate(copia)


def test_contrato_rechaza_productos_incoherentes(producto_json: dict[str, Any]) -> None:
    LluviaDistritos.model_validate(producto_json)

    def umbrales(d: dict[str, Any]) -> None:
        d["metodo"]["umbrales_mm"]["A"]["t2_mm"] = 1.0

    def dia_largo(d: dict[str, Any]) -> None:
        d["dias"][0]["fin"] = d["dias"][1]["fin"]

    def nivel_sin_probabilidades(d: dict[str, Any]) -> None:
        d["distritos"][0]["dias"][0]["probabilidades"] = None

    def probabilidad_creciente(d: dict[str, Any]) -> None:
        d["distritos"][0]["dias"][0]["probabilidades"] = [10, 20, 0]

    def sistema_repetido(d: dict[str, Any]) -> None:
        d["corridas"].append(d["corridas"][0])

    def solo_gefs(d: dict[str, Any]) -> None:
        d["corridas"] = [c for c in d["corridas"] if c["sistema"] == "ncep_gefs"]

    def dias_salteados(d: dict[str, Any]) -> None:
        d["dias"][1], d["dias"][2] = d["dias"][2], d["dias"][1]

    def tendencia_desfasada(d: dict[str, Any]) -> None:
        d["tendencia"]["inicio"] = d["dias"][0]["inicio"]

    def desordenados(d: dict[str, Any]) -> None:
        d["distritos"].reverse()

    def celda_inexistente(d: dict[str, Any]) -> None:
        d["distritos"][0]["celda"] = 999

    for cambio in (
        umbrales,
        dia_largo,
        nivel_sin_probabilidades,
        probabilidad_creciente,
        sistema_repetido,
        solo_gefs,
        dias_salteados,
        tendencia_desfasada,
        desordenados,
        celda_inexistente,
    ):
        _invalido(producto_json, cambio)


def test_contrato_del_archivo_rechaza_incoherencias(
    tmp_path: Path, catalogo: CatalogoDistritos
) -> None:
    _publicar(tmp_path, catalogo, _proveedor(catalogo, CORRIDAS_00, fallan=frozenset({GEFS})))
    datos = json.loads(gzip.decompress(_archivos(tmp_path)[0].read_bytes()))
    ArchivoLluvia.model_validate(datos)

    def dia(d: dict[str, Any]) -> dict[str, Any]:
        resultado: dict[str, Any] = d["sistemas"][0]["celdas"][0]["dias"][0]
        return resultado

    def conteo_excesivo(d: dict[str, Any]) -> None:
        dia(d)["alcanzan"][0] = 999

    def validos_mal(d: dict[str, Any]) -> None:
        dia(d)["validos"] = 3

    def conteos_cortos(d: dict[str, Any]) -> None:
        dia(d)["alcanzan"] = [0]

    def valores_de_mas(d: dict[str, Any]) -> None:
        d["descargados"] = ["ecmwf_aifs"]

    def miembros_de_menos(d: dict[str, Any]) -> None:
        dia(d)["lluvia_mm"] = dia(d)["lluvia_mm"][:5]
        dia(d)["validos"] = 5
        dia(d)["alcanzan"] = [min(a, 5) for a in dia(d)["alcanzan"]]

    for cambio in (conteo_excesivo, validos_mal, conteos_cortos, valores_de_mas, miembros_de_menos):
        copia = copy.deepcopy(datos)
        cambio(copia)
        with pytest.raises(ValidationError):
            ArchivoLluvia.model_validate(copia)
