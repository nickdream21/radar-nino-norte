"""Resumen legible del catálogo generado, para revisarlo antes de confirmarlo."""

from collections import Counter
from collections.abc import Sequence
from statistics import median

from radar.catalogo.construir import Comparacion, Informe
from radar.catalogo.zonas import EJEMPLOS_TABLA
from radar.contratos.distritos import CatalogoDistritos


def ejemplos_discrepantes(catalogo: CatalogoDistritos) -> list[str]:
    """Lugares nombrados en la tabla de zonas cuya zona calculada no coincide (o no existen)."""
    por_ubigeo = {d.ubigeo: d for d in catalogo.distritos}
    discrepantes: list[str] = []
    for ubigeo, esperada in EJEMPLOS_TABLA.items():
        distrito = por_ubigeo.get(ubigeo)
        if distrito is None:
            discrepantes.append(f"{ubigeo}: no está en el catálogo")
        elif distrito.zona != esperada:
            discrepantes.append(
                f"{ubigeo} {distrito.nombre}: tabla {esperada}, regla {distrito.zona}"
            )
    discrepantes.extend(
        f"{d.ubigeo} {d.nombre}: es de Tumbes y la regla da {d.zona}"
        for d in catalogo.distritos
        if d.ubigeo.startswith("24") and d.zona != "B"
    )
    return discrepantes


def resumen_catalogo(
    catalogo: CatalogoDistritos, informe: Informe, comparaciones: Sequence[Comparacion]
) -> str:
    distritos = catalogo.distritos
    lineas = [f"Distritos: {len(distritos)}"]
    for departamento, n in sorted(Counter(d.departamento for d in distritos).items()):
        lineas.append(f"  {departamento}: {n}")
    lineas.append("Por zona:")
    for zona, n in sorted(Counter(d.zona for d in distritos).items()):
        lineas.append(f"  {zona}: {n}")
    lats = [d.capital.latitud for d in distritos]
    lons = [d.capital.longitud for d in distritos]
    lineas.append(
        f"Caja de las capitales: latitud {min(lats)} a {max(lats)}, longitud {min(lons)} a"
        f" {max(lons)}"
    )
    oeste = min(distritos, key=lambda d: d.capital.longitud)
    este = max(distritos, key=lambda d: d.capital.longitud)
    norte = max(distritos, key=lambda d: d.capital.latitud)
    sur = min(distritos, key=lambda d: d.capital.latitud)
    for etiqueta, d in (("oeste", oeste), ("este", este), ("norte", norte), ("sur", sur)):
        lineas.append(f"  extremo {etiqueta}: {d.ubigeo} {d.nombre} ({d.capital.nombre})")

    lineas.append("Ejemplos de la tabla que la regla no reproduce:")
    lineas.extend(f"  {e}" for e in ejemplos_discrepantes(catalogo) or ["(ninguno)"])
    revisar = [d for d in distritos if d.revisar]
    lineas.append(f"Distritos para revisar: {len(revisar)}")
    for d in revisar:
        lineas.append(
            f"  {d.ubigeo} {d.nombre} ({d.provincia}) zona {d.zona}, {d.capital.altitud_m} m,"
            f" {d.distancia_costa_km} km al mar, {d.cuenca}: " + "; ".join(d.revisar)
        )
    lineas.append(f"Nombres sin tildes confirmadas: {len(informe.nombres_sin_confirmar)}")
    lineas.extend(f"  {n}" for n in informe.nombres_sin_confirmar)
    lineas.append(f"Tildes en desacuerdo entre fuentes: {len(informe.tildes_en_desacuerdo)}")
    lineas.extend(f"  {n}" for n in informe.tildes_en_desacuerdo)
    lineas.append(f"Capitales fuera del censo 2017: {informe.capitales_sin_censo or '(ninguna)'}")

    if comparaciones:
        distancias = [c.distancia_km for c in comparaciones]
        dif_altitud = [
            abs(c.altitud_catalogo_m - c.altitud_geonames_m)
            for c in comparaciones
            if c.altitud_geonames_m is not None
        ]
        lineas.append(
            f"Contraste con GeoNames: {len(comparaciones)} capitales; distancia mediana"
            f" {median(distancias):.2f} km, máxima {max(distancias):.1f} km; diferencia de"
            f" altitud mediana {median(dif_altitud):.0f} m, máxima {max(dif_altitud)} m"
        )
        for c in comparaciones:
            lineas.append(
                f"  {c.ubigeo} {c.distrito} [{c.zona}] vs {c.nombre_geonames}:"
                f" {c.distancia_km:.2f} km, {c.altitud_catalogo_m} m vs"
                f" {c.altitud_geonames_m} m"
            )
    return "\n".join(lineas)
