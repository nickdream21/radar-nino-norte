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

La orden descarga todas las fuentes (gasta unas 330 unidades de la cuota diaria de Open-Meteo, una por capital) y escribe el archivo. Hay que regenerarlo cuando el INEI cree o modifique distritos o cuando cambie la regla de zonas.

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

La regla está documentada y probada en `pipeline/src/radar/catalogo/zonas.py`. Se evalúa en este orden con los datos de la capital:

1. **D** si drena al Atlántico (cuenca del Marañón), a cualquier altitud.
2. **B** si es de Tumbes.
3. **D** por encima de 3000 m.
4. **C** entre 1000 y 3000 m.
5. **B** entre 200 y 1000 m.
6. **B** por debajo de 200 m y a más de 60 km del mar (llanura del Alto Piura, Chira medio, Olmos-Motupe).
7. **A** en el resto.

El umbral de 3000 m (y no los 2500 m del texto de la tabla) y el límite de 60 km hacen que todos los ejemplos de la tabla caigan en su zona. `revisar` explica, distrito por distrito, por qué la zona es dudosa: altitud cerca de un umbral, sierra del Pacífico entre 2500 y 3000 m, distancia al mar cerca de 60 km, capital a menos de 5 km de la divisoria o capital ubicada con GeoNames.
