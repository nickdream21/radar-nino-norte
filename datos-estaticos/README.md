# Datos estáticos

Datos que no llegan por la ingesta horaria: los que se mantienen a mano y los que se regeneran a mano desde sus fuentes. El pipeline los valida al leerlos: si un archivo no cumple su contrato, el bloque correspondiente se trata como fuente caída.

## `enfen.json`

Último comunicado oficial del ENFEN (contrato `ComunicadoEnfen` en `pipeline/src/radar/contratos/nino.py`).

| Campo    | Contenido                                                                     |
| -------- | ----------------------------------------------------------------------------- |
| `estado` | Estado del sistema de alerta, copiado tal cual del comunicado                 |
| `numero` | Número del comunicado, `NN-AAAA`                                              |
| `fecha`  | Fecha de emisión con zona horaria de Lima, p. ej. `2026-11-13T00:00:00-05:00` |
| `enlace` | Dirección del comunicado (PDF) o, si no se tiene, del sitio del ENFEN         |

Actualizarlo cada vez que el ENFEN emita un comunicado (habitualmente cada dos semanas). La fecha se publica para que la web pueda avisar cuando el comunicado sea antiguo.

## `distritos.json`

Catálogo de los 327 distritos de Tumbes (13), Piura (65), Lambayeque (38), La Libertad (84) y Cajamarca (127), con la capital de cada uno y su zona pluviométrica. Contrato `CatalogoDistritos` en `pipeline/src/radar/contratos/distritos.py`; el esquema está en `packages/contratos/esquemas/catalogo_distritos.schema.json`. Se lee y valida con `radar.catalogo.cargar_catalogo`, que además recalcula la zona de cada distrito y falla si no coincide con la guardada.

No se edita a mano. Se regenera, se revisa el resumen que imprime y se confirma:

```sh
cd pipeline
uv run radar generar-distritos
```

La orden descarga todas las fuentes (gasta unas 330 unidades de la cuota diaria de Open-Meteo, una por capital) y escribe el archivo. Hay que regenerarlo cuando el INEI cree o modifique distritos.

Si solo cambia la regla de zonas, no hace falta descargar nada:

```sh
cd pipeline
uv run radar recalcular-zonas
```

Recalcula `zona` y `revisar` con los datos ya guardados en el archivo, imprime los distritos que cambian de zona y deja el resto del archivo intacto, byte a byte. La distancia a la divisoria Pacífico-Atlántico no se guarda como campo; se relee del motivo de `revisar` que la anota (solo existe para capitales a 5 km o menos de la divisoria, las únicas en que cuenta).

### Procedencia de cada campo

Todas las fuentes se descargaron el 23-nov-2026. El propio archivo repite la procedencia en `fuentes`, con la hora exacta de cada descarga.

| Campo                                                    | Fuente                                                                                                                                                                                                                          | Licencia                                                                                                     | Atribución                                                                                                                                                               |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ubigeo`, `nombre`, `provincia`, `departamento` (letras) | INEI, Registro Nacional de Municipalidades (RENAMU) 2026, módulo 1 ([datosabiertos.gob.pe](https://www.datosabiertos.gob.pe/dataset/registro-nacional-de-municipalidades-renamu-2026-instituto-nacional-de-estad%C3%ADstica-e)) | ODC-By 1.0                                                                                                   | Instituto Nacional de Estadística e Informática (INEI), RENAMU 2026                                                                                                      |
| `capital.nombre`, `capital.latitud`, `capital.longitud`  | INEI, centros poblados de los Censos Nacionales 2017, capa `Interoperabilidad:ig_centropoblado` del geoservidor `geoespacial.inei.gob.pe` (el centro poblado `0001` de cada distrito es su capital)                             | Información pública del Estado peruano; el servicio no declara restricciones de acceso ni licencia explícita | INEI, Censos Nacionales 2017                                                                                                                                             |
| `capital` de Alto Trujillo (130112)                      | GeoNames, lugar 13562177 (el distrito se creó después del censo)                                                                                                                                                                | CC BY 4.0                                                                                                    | GeoNames (www.geonames.org)                                                                                                                                              |
| `capital.altitud_m`                                      | Copernicus DEM GLO-90 (90 m) servido por la [Open-Meteo Elevation API](https://open-meteo.com/en/docs/elevation-api), en el punto de la capital                                                                                 | Licencia de Copernicus DEM (uso y redistribución gratuitos); Open-Meteo CC BY 4.0                            | Copernicus DEM GLO-90 © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, provisto en el marco de COPERNICUS por la Unión Europea y la ESA; Open-Meteo.com |
| `vertiente`, `cuenca`                                    | ANA, unidades hidrográficas (Pfafstetter) del GeoSNIRH; solo se guarda el nombre de la unidad que contiene a la capital y su región hidrográfica                                                                                | Información pública del Estado peruano                                                                       | Autoridad Nacional del Agua (ANA)                                                                                                                                        |
| `distancia_costa_km`                                     | Natural Earth 1:10m, línea de costa v5.1.2                                                                                                                                                                                      | Dominio público                                                                                              | Made with Natural Earth                                                                                                                                                  |
| Tildes y eñes de los nombres                             | Etiquetas en español de Wikidata, enlazadas por el identificador de GeoNames (P1566), y nombres de GeoNames                                                                                                                     | Wikidata CC0 1.0; GeoNames CC BY 4.0                                                                         | Wikidata; GeoNames                                                                                                                                                       |
| `zona`, `revisar`                                        | Calculados con la regla de `pipeline/src/radar/catalogo/zonas.py`                                                                                                                                                               | Propios del proyecto (MIT)                                                                                   | —                                                                                                                                                                        |

GADM no se usa: su licencia prohíbe redistribuir los datos.

### Nombres

Las letras, los espacios y los guiones son siempre los del INEI, que escribe en mayúsculas y sin tildes. De Wikidata o GeoNames solo se copian las tildes, y solo si el nombre candidato, sin tildes ni guiones, coincide letra por letra con el del INEI. Por eso se conservan grafías del INEI como «Tambo Grande» o «Santa Cruz de Toled» aunque otras fuentes escriban «Tambogrande» o «Santa Cruz de Toledo». Los nombres sin ningún candidato que coincida se dejan sin tildes y el generador los lista.

`fuentes/wikidata-etiquetas.json` es la respuesta de Wikidata usada para las tildes (CC0). `query.wikidata.org` rechaza a los clientes automáticos sin contacto en el agente de usuario, así que la orden usa esta instantánea; con `--contacto-wikidata <url o correo>` la renueva antes de generar.

### Zonas

La zona **solo elige los umbrales de lluvia diaria** de cada distrito. No dice cómo le afecta El Niño costero: cualquier texto sobre ese efecto debe depender de `vertiente`, nunca de `zona`.

La regla está documentada y probada en `pipeline/src/radar/catalogo/zonas.py`. Es la revisada por el meteorólogo del proyecto y se evalúa en este orden con los datos de la capital; gana la primera que se cumple:

1. Vertiente atlántica (cuenca del Marañón): **C** por debajo de 1500 m; **D** desde 1500 m.
2. **B** si es de Tumbes.
3. **D** si está en la cuenca del Santa (unidad hidrográfica `Cuenca Santa` de la ANA), a cualquier altitud.
4. **D** por encima de 3000 m.
5. **C** de 1000 a 3000 m.
6. **A** por debajo de 1000 m si la capital está a menos de 20 km del mar o al sur de la latitud -6,75°.
7. **B** de 200 a 1000 m.
8. **B** por debajo de 200 m y a más de 60 km del mar (llanura del Alto Piura, Chira medio, Olmos-Motupe).
9. **A** en el resto.

Las zonas son A costa y valles áridos, B Tumbes y piedemonte, C sierra occidental y valles bajos de la vertiente oriental, D sierra alta.

Los cortes (3000 m, 1500 m, 60 km, 20 km y -6,75°) son **criterio experto provisional**, pendiente de contraste con percentiles de lluvia de CHIRPS.

Excepciones: Bolívar (061102), La Florida (061106) y Lalaquiz (200305) tienen la zona C fijada a mano (`ZONAS_FORZADAS`) por estar en ladera húmeda entre 900 y 1000 m; es criterio del meteorólogo con confianza media-baja. El motivo de cada excepción se guarda en su `revisar`.

`revisar` explica, distrito por distrito, por qué la zona es dudosa: altitud a menos del margen de un umbral (50 m alrededor de 200 m, 100 m alrededor de 1000 m, 150 m alrededor de 1500 m en la vertiente atlántica y de 3000 m) cuando eso cambiaría la zona, distancia al mar cerca de 60 km, capital a menos de 5 km de la divisoria si en la otra vertiente tendría otra zona, zona fijada a mano, capital ubicada con GeoNames o fuera de las unidades hidrográficas, y los distritos que el meteorólogo pidió contrastar con percentiles (Chongoyape y Canoas de Punta Sal).
