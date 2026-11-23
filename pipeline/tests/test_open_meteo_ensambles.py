import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from radar.fuentes import FuenteNoDisponible
from radar.fuentes.open_meteo_ensambles import (
    SISTEMAS,
    DiaLluvia,
    EnsamblesLluvia,
    FuenteEnsamblesOpenMeteo,
    LimitadorCuota,
    Punto,
    SeriePunto,
    Sistema,
    coste_llamada,
    interpretar_meta,
    interpretar_respuesta,
    puntos_por_llamada,
    url_consulta,
)
from tests.ayudas import (
    AHORA,
    OM_ENSAMBLE,
    OM_ERROR,
    OM_META,
    Esperas,
    ahora_fijo,
    cliente_simulado,
    leer_fixture,
    politica_sin_espera,
)

CORTO = {Sistema.IFS: "ifs", Sistema.AIFS: "aifs", Sistema.GEFS: "gefs"}
POR_MODELO = {SISTEMAS[s].modelo: s for s in Sistema}
PIURA = Punto(id="piura", latitud=-5.1945, longitud=-80.6328)
TUMBES = Punto(id="tumbes", latitud=-3.5669, longitud=-80.4515)
PUNTOS = [PIURA, TUMBES]
INICIALIZACION = {
    Sistema.IFS: datetime(2026, 11, 23, 0, tzinfo=UTC),
    Sistema.AIFS: datetime(2026, 11, 23, 6, tzinfo=UTC),
    Sistema.GEFS: datetime(2026, 11, 23, 6, tzinfo=UTC),
}
PRIMER_DIA = datetime(2026, 11, 23, 12, tzinfo=UTC)


def _real(sistema: Sistema) -> str:
    return leer_fixture(OM_ENSAMBLE.format(sistema=CORTO[sistema]))


def _meta(sistema: Sistema) -> str:
    return leer_fixture(OM_META.format(sistema=CORTO[sistema]))


def _lugares(sistema: Sistema) -> list[dict[str, Any]]:
    datos: list[dict[str, Any]] = json.loads(_real(sistema))
    return datos


def _json(httpx_estado: int, texto: str) -> httpx.Response:
    return httpx.Response(
        httpx_estado, text=texto, headers={"content-type": "application/json; charset=utf-8"}
    )


Manejador = Callable[[httpx.Request], httpx.Response]


def _api(
    ensambles: dict[Sistema, Manejador] | None = None,
    metas: dict[Sistema, Manejador] | None = None,
    pedidas: list[httpx.Request] | None = None,
) -> Manejador:
    """Simula la API: grabaciones reales salvo lo que se sustituya por sistema."""

    def manejador(request: httpx.Request) -> httpx.Response:
        if pedidas is not None:
            pedidas.append(request)
        if request.url.path.startswith("/data/"):
            sistema = POR_MODELO[request.url.path.split("/")[2]]
            if metas and sistema in metas:
                return metas[sistema](request)
            return _json(200, _meta(sistema))
        sistema = POR_MODELO[request.url.params["models"]]
        if ensambles and sistema in ensambles:
            return ensambles[sistema](request)
        return _json(200, _real(sistema))

    return manejador


def _fuente(
    manejador: Manejador, puntos: list[Punto] = PUNTOS, **opciones: Any
) -> FuenteEnsamblesOpenMeteo:
    return FuenteEnsamblesOpenMeteo(
        puntos,
        cliente=cliente_simulado(manejador),
        politica=politica_sin_espera(),
        limitador=LimitadorCuota(esperar=Esperas()),
        ahora=ahora_fijo,
        **opciones,
    )


# --- Respuestas reales -----------------------------------------------------------------


@pytest.mark.parametrize("sistema", list(Sistema))
def test_respuesta_real_de_cada_sistema(sistema: Sistema) -> None:
    series = interpretar_respuesta(_real(sistema), sistema, PUNTOS, PRIMER_DIA)

    miembros = SISTEMAS[sistema].miembros
    assert [s.punto for s in series] == PUNTOS
    for serie in series:
        assert len(serie.dias) == 7
        assert serie.dias[0].inicio == PRIMER_DIA
        assert serie.dias[-1].inicio == PRIMER_DIA + timedelta(days=6)
        assert all(len(d.lluvia_mm) == miembros for d in serie.dias)
        assert all(d.miembros_validos == miembros for d in serie.dias)


def test_valores_reales_fijados() -> None:
    piura, tumbes = interpretar_respuesta(_real(Sistema.IFS), Sistema.IFS, PUNTOS, PRIMER_DIA)

    # Control y miembro 1 del primer día, sumados de 12 a 12 UTC sobre la grabación.
    assert piura.dias[0].lluvia_mm[:2] == (1.1, 0.8)
    assert tumbes.dias[2].lluvia_mm[:2] == (17.6, 11.6)


def test_la_celda_devuelta_no_es_la_pedida() -> None:
    piura, tumbes = interpretar_respuesta(_real(Sistema.AIFS), Sistema.AIFS, PUNTOS, PRIMER_DIA)

    # Open-Meteo elige la celda de 0.25° según su máscara de tierra, no la más cercana.
    assert (piura.celda.latitud, piura.celda.longitud) == (-5.25, -80.75)
    assert (piura.punto.latitud, piura.punto.longitud) == (-5.1945, -80.6328)
    assert piura.celda.altitud_m == 27.0
    # La celda de Tumbes ciudad tiene altitud 0: el modelo la trata como costa o mar.
    assert (tumbes.celda.latitud, tumbes.celda.longitud, tumbes.celda.altitud_m) == (
        -3.5,
        -80.5,
        0.0,
    )


def test_cada_sistema_tiene_su_propia_altitud_de_celda() -> None:
    altitudes = {
        s: interpretar_respuesta(_real(s), s, PUNTOS, PRIMER_DIA)[0].celda.altitud_m
        for s in Sistema
    }
    assert altitudes == {Sistema.IFS: 43.0, Sistema.AIFS: 27.0, Sistema.GEFS: 47.0}


def test_obtener_entrega_los_tres_sistemas() -> None:
    pedidas: list[httpx.Request] = []
    fuente = _fuente(_api(pedidas=pedidas))

    resultado = fuente.obtener()

    assert fuente.id == "open-meteo-ensambles"
    assert resultado.obtenido_en == AHORA
    assert resultado.fallos == {}
    assert resultado.sin_corrida_nueva == {}
    assert set(resultado.sistemas) == set(Sistema)
    for sistema, pronostico in resultado.sistemas.items():
        assert pronostico.inicializacion == INICIALIZACION[sistema]
        assert pronostico.primer_dia == PRIMER_DIA
        assert pronostico.miembros == SISTEMAS[sistema].miembros
        assert len(pronostico.puntos) == 2
    # Por sistema: meta, datos y meta otra vez para confirmar que no cambió la corrida.
    assert len(pedidas) == 9
    datos = [r for r in pedidas if r.url.path == "/v1/ensemble"]
    assert {r.url.params["models"] for r in datos} == {
        "ecmwf_ifs025_ensemble",
        "ecmwf_aifs025_ensemble",
        "ncep_gefs025",
    }


def test_url_de_consulta() -> None:
    url = httpx.URL(url_consulta(SISTEMAS[Sistema.GEFS], PUNTOS))

    assert url.host == "ensemble-api.open-meteo.com"
    assert dict(url.params) == {
        "latitude": "-5.1945,-3.5669",
        "longitude": "-80.6328,-80.4515",
        "hourly": "precipitation",
        "models": "ncep_gefs025",
        "forecast_days": "9",
        "temporal_resolution": "native",
        "timeformat": "unixtime",
        "cell_selection": "land",
        "elevation": "nan,nan",
    }


# --- Días parciales --------------------------------------------------------------------


def test_dia_parcial_al_principio_no_se_entrega() -> None:
    # La serie empieza a las 00 UTC del 23: el día del 22 a las 12 UTC está incompleto.
    with pytest.raises(FuenteNoDisponible, match="solo 7 días completos desde 2026-11-22"):
        interpretar_respuesta(_real(Sistema.IFS), Sistema.IFS, PUNTOS, PRIMER_DIA - timedelta(1))


def test_dia_parcial_al_final_no_cuenta() -> None:
    # La serie termina el 1-dic a las 21 UTC: el día del 1-dic no está completo, así que
    # desde el 25 solo hay 6 días (25 al 30) y el sistema llega incompleto.
    with pytest.raises(FuenteNoDisponible, match="solo 6 días completos"):
        interpretar_respuesta(_real(Sistema.IFS), Sistema.IFS, PUNTOS, PRIMER_DIA + timedelta(2))


def test_serie_recortada_al_final() -> None:
    lugares = _lugares(Sistema.AIFS)
    for lugar in lugares:
        horario = lugar["hourly"]
        for clave in horario:
            horario[clave] = horario[clave][:-8]  # quita las últimas 48 h

    with pytest.raises(FuenteNoDisponible, match="días completos"):
        interpretar_respuesta(json.dumps(lugares), Sistema.AIFS, PUNTOS, PRIMER_DIA)


# --- Miembros nulos y valores sucios ---------------------------------------------------


@pytest.mark.parametrize("sucio", [None, "NaN", -99.99, "texto"])
def test_miembro_con_hueco_no_cuenta_ese_dia(sucio: object) -> None:
    lugares = _lugares(Sistema.GEFS)
    horario = lugares[0]["hourly"]
    # Paso que termina el 24-nov a las 18 UTC: segundo día (24 12 UTC → 25 12 UTC).
    i = horario["time"].index(int(datetime(2026, 11, 24, 18, tzinfo=UTC).timestamp()))
    horario["precipitation_member07"][i] = sucio
    texto = json.dumps(lugares).replace('"NaN"', "NaN")

    piura, tumbes = interpretar_respuesta(texto, Sistema.GEFS, PUNTOS, PRIMER_DIA)

    assert piura.dias[1].lluvia_mm[7] is None
    assert piura.dias[1].miembros_validos == 30
    assert all(d.miembros_validos == 31 for d in piura.dias if d is not piura.dias[1])
    assert all(d.miembros_validos == 31 for d in tumbes.dias)


def test_miembro_entero_nulo() -> None:
    lugares = _lugares(Sistema.IFS)
    horario = lugares[1]["hourly"]
    horario["precipitation_member50"] = [None] * len(horario["time"])

    _, tumbes = interpretar_respuesta(json.dumps(lugares), Sistema.IFS, PUNTOS, PRIMER_DIA)

    assert all(d.lluvia_mm[50] is None and d.miembros_validos == 50 for d in tumbes.dias)


def test_falta_un_miembro_es_respuesta_incompleta() -> None:
    lugares = _lugares(Sistema.IFS)
    del lugares[0]["hourly"]["precipitation_member33"]

    with pytest.raises(FuenteNoDisponible, match="faltan 1 miembros"):
        interpretar_respuesta(json.dumps(lugares), Sistema.IFS, PUNTOS, PRIMER_DIA)


def test_miembro_con_menos_horas() -> None:
    lugares = _lugares(Sistema.IFS)
    lugares[0]["hourly"]["precipitation"].pop()

    with pytest.raises(FuenteNoDisponible, match="no tiene todas las horas"):
        interpretar_respuesta(json.dumps(lugares), Sistema.IFS, PUNTOS, PRIMER_DIA)


def test_faltan_lugares() -> None:
    lugares = _lugares(Sistema.IFS)[:1]

    with pytest.raises(FuenteNoDisponible, match="1 lugares para 2 puntos"):
        interpretar_respuesta(json.dumps(lugares), Sistema.IFS, PUNTOS, PRIMER_DIA)


def test_un_solo_punto_llega_como_objeto() -> None:
    lugar = _lugares(Sistema.GEFS)[1]

    (serie,) = interpretar_respuesta(json.dumps(lugar), Sistema.GEFS, [TUMBES], PRIMER_DIA)

    assert serie.celda.latitud == -3.5


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (lambda lugar: lugar.pop("latitude"), "qué celda usó"),
        (lambda lugar: lugar.__setitem__("latitude", 95.0), "datos inválidos"),
        (lambda lugar: lugar.pop("hourly"), "sin datos horarios"),
        (lambda lugar: lugar["hourly"].pop("time"), "sin horas"),
        (lambda lugar: lugar["hourly"]["time"].__setitem__(3, True), "hora no reconocida"),
        (lambda lugar: lugar["hourly"]["time"].__setitem__(3, "ayer"), "hora no reconocida"),
    ],
)
def test_lugar_mal_formado(cambio: Callable[[dict[str, Any]], object], mensaje: str) -> None:
    lugares = _lugares(Sistema.AIFS)
    cambio(lugares[0])

    with pytest.raises(FuenteNoDisponible, match=mensaje):
        interpretar_respuesta(json.dumps(lugares), Sistema.AIFS, PUNTOS, PRIMER_DIA)


def test_paso_irregular_por_fila_perdida() -> None:
    lugares = _lugares(Sistema.AIFS)
    horario = lugares[0]["hourly"]
    for clave in horario:
        del horario[clave][10]

    with pytest.raises(FuenteNoDisponible, match="no van cada 6 h"):
        interpretar_respuesta(json.dumps(lugares), Sistema.AIFS, PUNTOS, PRIMER_DIA)


def _horas_iso(lugares: list[dict[str, Any]], zona: str = "") -> None:
    for lugar in lugares:
        horario = lugar["hourly"]
        horario["time"] = [
            datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M") + zona
            for t in horario["time"]
        ]


def test_hora_sin_zona_con_desfase_declarado() -> None:
    lugares = _lugares(Sistema.GEFS)
    _horas_iso(lugares)  # como con timeformat=iso8601: "2026-11-23T00:00" y utc_offset 0

    series = interpretar_respuesta(json.dumps(lugares), Sistema.GEFS, PUNTOS, PRIMER_DIA)

    assert series[0].dias[0].inicio == PRIMER_DIA


def test_hora_local_con_desfase_se_pasa_a_utc() -> None:
    lugares = _lugares(Sistema.GEFS)
    for lugar in lugares:
        lugar["utc_offset_seconds"] = -5 * 3600
        lugar["hourly"]["time"] = [
            (datetime.fromtimestamp(t, UTC) - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
            for t in lugar["hourly"]["time"]
        ]

    series = interpretar_respuesta(json.dumps(lugares), Sistema.GEFS, PUNTOS, PRIMER_DIA)
    original = interpretar_respuesta(_real(Sistema.GEFS), Sistema.GEFS, PUNTOS, PRIMER_DIA)

    assert series == original


def test_hora_con_zona_explicita() -> None:
    lugares = _lugares(Sistema.GEFS)
    _horas_iso(lugares, "+00:00")
    for lugar in lugares:
        del lugar["utc_offset_seconds"]

    series = interpretar_respuesta(json.dumps(lugares), Sistema.GEFS, PUNTOS, PRIMER_DIA)

    assert series[1].dias[0].inicio == PRIMER_DIA


def test_hora_sin_zona_ni_desfase_falla() -> None:
    lugares = _lugares(Sistema.GEFS)
    _horas_iso(lugares)
    for lugar in lugares:
        del lugar["utc_offset_seconds"]

    with pytest.raises(FuenteNoDisponible, match="sin zona horaria"):
        interpretar_respuesta(json.dumps(lugares), Sistema.GEFS, PUNTOS, PRIMER_DIA)


def test_corte_inexacto_se_informa() -> None:
    # Pasos de 6 h empezando a las 03 UTC: cada día tendría un intervalo 09-15 partido.
    lugares = _lugares(Sistema.AIFS)
    for lugar in lugares:
        lugar["hourly"]["time"] = [t + 3 * 3600 for t in lugar["hourly"]["time"]]

    with pytest.raises(FuenteNoDisponible, match="cruza las 12 UTC"):
        interpretar_respuesta(json.dumps(lugares), Sistema.AIFS, PUNTOS, PRIMER_DIA)


# --- Errores de la API y sistemas caídos -----------------------------------------------


def test_error_de_la_api_en_el_cuerpo() -> None:
    with pytest.raises(FuenteNoDisponible, match="error de la API: Invalid value"):
        interpretar_respuesta(leer_fixture(OM_ERROR), Sistema.IFS, PUNTOS, PRIMER_DIA)


@pytest.mark.parametrize("texto", ["no es json", "<html></html>", "42"])
def test_respuesta_que_no_es_la_esperada(texto: str) -> None:
    with pytest.raises(FuenteNoDisponible):
        interpretar_respuesta(texto, Sistema.IFS, PUNTOS, PRIMER_DIA)


def test_error_400_de_un_sistema_no_tumba_a_los_demas() -> None:
    error = _json(400, leer_fixture(OM_ERROR))
    fuente = _fuente(_api(ensambles={Sistema.AIFS: lambda _: error}))

    resultado = fuente.obtener()

    assert set(resultado.sistemas) == {Sistema.IFS, Sistema.GEFS}
    assert "HTTP 400" in resultado.fallos[Sistema.AIFS]


def test_sistema_caido_se_identifica_y_los_otros_se_entregan() -> None:
    caido = httpx.Response(503)
    fuente = _fuente(_api(ensambles={Sistema.GEFS: lambda _: caido}))

    resultado = fuente.obtener()

    assert set(resultado.sistemas) == {Sistema.IFS, Sistema.AIFS}
    assert resultado.fallos[Sistema.GEFS].endswith("HTTP 503 tras 3 intentos")


def test_sistema_incompleto_se_identifica() -> None:
    lugares = _lugares(Sistema.IFS)
    del lugares[1]["hourly"]["precipitation_member01"]
    incompleto = _json(200, json.dumps(lugares))
    fuente = _fuente(_api(ensambles={Sistema.IFS: lambda _: incompleto}))

    resultado = fuente.obtener()

    assert "tumbes: respuesta incompleta" in resultado.fallos[Sistema.IFS]
    assert set(resultado.sistemas) == {Sistema.AIFS, Sistema.GEFS}


def test_respuesta_html_se_rechaza() -> None:
    html = httpx.Response(
        200, text="<html>mantenimiento</html>", headers={"content-type": "text/html"}
    )
    fuente = _fuente(_api(ensambles={Sistema.IFS: lambda _: html}))

    assert "HTML" in fuente.obtener().fallos[Sistema.IFS]


def test_todos_los_sistemas_caidos() -> None:
    def caido(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    with pytest.raises(FuenteNoDisponible, match="fallaron todos los sistemas"):
        _fuente(caido).obtener()


# --- Corridas --------------------------------------------------------------------------


def test_meta_real() -> None:
    assert {s: interpretar_meta(_meta(s)) for s in Sistema} == INICIALIZACION


@pytest.mark.parametrize(
    "texto",
    ["{}", "no", '{"last_run_initialisation_time": "ayer"}', '{"last_run_initialisation_time": 0}'],
)
def test_meta_mal_formado(texto: str) -> None:
    with pytest.raises(ValueError):
        interpretar_meta(texto)


def test_sin_corrida_nueva_no_descarga() -> None:
    pedidas: list[httpx.Request] = []
    conocidas = {
        Sistema.IFS: INICIALIZACION[Sistema.IFS],
        Sistema.GEFS: INICIALIZACION[Sistema.GEFS],
    }
    fuente = _fuente(_api(pedidas=pedidas), corridas_conocidas=conocidas)

    resultado = fuente.obtener()

    assert resultado.sin_corrida_nueva == conocidas
    assert set(resultado.sistemas) == {Sistema.AIFS}
    assert [r.url.params["models"] for r in pedidas if r.url.path == "/v1/ensemble"] == [
        "ecmwf_aifs025_ensemble"
    ]


def test_corrida_vieja_conocida_si_descarga() -> None:
    vieja = {Sistema.IFS: INICIALIZACION[Sistema.IFS] - timedelta(hours=12)}

    resultado = _fuente(_api(), corridas_conocidas=vieja).obtener()

    assert Sistema.IFS in resultado.sistemas


def test_sin_meta_la_corrida_queda_desconocida() -> None:
    fuente = _fuente(_api(metas={s: (lambda _: httpx.Response(404)) for s in Sistema}))

    resultado = fuente.obtener()

    for pronostico in resultado.sistemas.values():
        assert pronostico.inicializacion is None
        # Sin la corrida se cuenta desde ahora (23-nov 15 UTC): el primer día es el 24.
        assert pronostico.primer_dia == PRIMER_DIA + timedelta(days=1)


def test_corrida_que_cambia_durante_la_descarga() -> None:
    metas = iter([_meta(Sistema.GEFS), json.dumps({"last_run_initialisation_time": 1795435200})])
    fuente = _fuente(
        _api(metas={Sistema.GEFS: lambda _: _json(200, next(metas))}), sistemas=[Sistema.GEFS]
    )

    with pytest.raises(FuenteNoDisponible, match="la corrida cambió durante la descarga"):
        fuente.obtener()


def test_meta_que_falla_despues_de_descargar() -> None:
    respuestas = iter([_json(200, _meta(Sistema.GEFS)), httpx.Response(404)])
    fuente = _fuente(
        _api(metas={Sistema.GEFS: lambda _: next(respuestas)}), sistemas=[Sistema.GEFS]
    )

    pronostico = fuente.obtener().sistemas[Sistema.GEFS]

    assert pronostico.inicializacion is None


# --- Cuota y lotes ---------------------------------------------------------------------


def test_coste_de_las_llamadas() -> None:
    assert coste_llamada(1, 51) == pytest.approx(5.1)
    assert coste_llamada(1, 31) == pytest.approx(3.1)
    assert coste_llamada(1, 5) == 1.0
    assert coste_llamada(1, 51, dias=28) == pytest.approx(10.2)
    # 300 puntos con los tres sistemas: 3 990 llamadas.
    total = sum(coste_llamada(300, SISTEMAS[s].miembros) for s in Sistema)
    assert total == pytest.approx(3990)
    assert puntos_por_llamada(51) == 98
    assert puntos_por_llamada(31) == 161


def test_muchos_puntos_van_en_lotes_respetando_el_minuto() -> None:
    reloj = [0.0]
    esperas = Esperas()

    def esperar(segundos: float) -> None:
        esperas.append(segundos)
        reloj[0] += segundos

    puntos = [Punto(id=f"p{i}", latitud=-5.0, longitud=-80.0) for i in range(110)]
    lugar = _lugares(Sistema.IFS)[0]
    tamanos: list[int] = []

    def ensamble(request: httpx.Request) -> httpx.Response:
        n = len(request.url.params["latitude"].split(","))
        tamanos.append(n)
        return _json(200, json.dumps([lugar] * n))

    fuente = FuenteEnsamblesOpenMeteo(
        puntos,
        sistemas=[Sistema.IFS],
        cliente=cliente_simulado(_api(ensambles={Sistema.IFS: ensamble})),
        politica=politica_sin_espera(),
        limitador=LimitadorCuota(reloj=lambda: reloj[0], esperar=esperar),
        ahora=ahora_fijo,
    )

    pronostico = fuente.obtener().sistemas[Sistema.IFS]

    assert tamanos == [98, 12]
    assert esperas == [60.0]  # 499.8 + 61.2 > 540: el segundo lote espera al minuto
    assert [s.punto.id for s in pronostico.puntos] == [p.id for p in puntos]
    assert fuente.coste_estimado() == pytest.approx(561)


def test_limitador_por_hora() -> None:
    reloj = [0.0]
    esperas = Esperas()

    def esperar(segundos: float) -> None:
        esperas.append(segundos)
        reloj[0] += segundos

    limitador = LimitadorCuota(
        limites=((60.0, 100.0), (3600.0, 150.0)), reloj=lambda: reloj[0], esperar=esperar
    )
    limitador.reservar(90)
    limitador.reservar(50)  # espera al minuto
    limitador.reservar(50)  # ya caben en el minuto, pero no en la hora

    assert esperas == [60.0, 3540.0]
    with pytest.raises(ValueError, match="no cabe"):
        limitador.reservar(101)


def test_limitador_sin_espera_si_cabe() -> None:
    esperas = Esperas()
    limitador = LimitadorCuota(esperar=esperas, reloj=lambda: 0.0)
    for _ in range(5):
        limitador.reservar(100)

    assert esperas == []


# --- Validación del modelo interno -----------------------------------------------------


def test_constructor_valida_los_puntos() -> None:
    with pytest.raises(ValueError, match="al menos un punto"):
        FuenteEnsamblesOpenMeteo([])
    with pytest.raises(ValueError, match="únicos"):
        FuenteEnsamblesOpenMeteo([PIURA, PIURA])


@pytest.mark.parametrize(
    ("campos", "mensaje"),
    [
        ({"inicio": PRIMER_DIA + timedelta(hours=1)}, "12:00 UTC"),
        ({"lluvia_mm": (1.0, -1.0), "miembros_validos": 2}, "negativa"),
        ({"miembros_validos": 2}, "miembros_validos"),
        ({"inicio": datetime(2026, 11, 23, 12)}, "timezone"),  # noqa: DTZ001
    ],
)
def test_dia_invalido(campos: dict[str, Any], mensaje: str) -> None:
    datos: dict[str, Any] = {"inicio": PRIMER_DIA, "lluvia_mm": (1.0, None), "miembros_validos": 1}
    datos.update(campos)
    with pytest.raises(ValidationError, match=mensaje):
        DiaLluvia(**datos)


def test_dia_en_hora_de_lima_se_guarda_en_utc() -> None:
    siete_lima = datetime(2026, 11, 23, 7, tzinfo=timezone(timedelta(hours=-5)))

    dia = DiaLluvia(inicio=siete_lima, lluvia_mm=(1.0,), miembros_validos=1)

    assert dia.inicio == PRIMER_DIA
    assert dia.inicio.tzinfo == UTC


def test_serie_y_resultado_invalidos() -> None:
    (serie, _) = interpretar_respuesta(_real(Sistema.GEFS), Sistema.GEFS, PUNTOS, PRIMER_DIA)
    dias = list(serie.dias)
    dias[3], dias[4] = dias[4], dias[3]
    with pytest.raises(ValidationError, match="consecutivos"):
        SeriePunto(punto=serie.punto, celda=serie.celda, dias=tuple(dias))

    pronostico = _fuente(_api(), sistemas=[Sistema.GEFS]).obtener().sistemas[Sistema.GEFS]
    with pytest.raises(ValidationError, match="primer_dia"):
        pronostico.model_validate(
            pronostico.model_dump() | {"primer_dia": PRIMER_DIA + timedelta(days=1)}
        )
    with pytest.raises(ValidationError, match="número de miembros"):
        pronostico.model_validate(pronostico.model_dump() | {"miembros": 51})
    with pytest.raises(ValidationError, match="dos estados"):
        EnsamblesLluvia(
            obtenido_en=AHORA,
            sistemas={Sistema.GEFS: pronostico},
            fallos={Sistema.GEFS: "x"},
            sin_corrida_nueva={},
        )
    with pytest.raises(ValidationError, match="inconsistente"):
        EnsamblesLluvia(
            obtenido_en=AHORA, sistemas={Sistema.IFS: pronostico}, fallos={}, sin_corrida_nueva={}
        )
