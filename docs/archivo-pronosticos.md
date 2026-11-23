# Archivo de pronósticos de lluvia (formato 1)

Cada ejecución de `radar publicar` que descarga al menos un sistema de ensambles deja un archivo `lluvia-distritos-AAAAMMDDTHHMMSSZ.json.gz` (hora UTC de la ejecución). Se guardan como activos de los releases `archivo-pronosticos-AAAA-MM` del repositorio ([ADR 0006](adr/0006-archivo-de-pronosticos-en-releases.md)). Son la base de la verificación y de la calibración de M1.

Esquema JSON completo: [`esquemas/archivo_lluvia.schema.json`](esquemas/archivo_lluvia.schema.json) (se regenera con `uv run radar exportar-esquema-archivo`).

## Leerlo sin el pipeline

```sh
gh release download archivo-pronosticos-2026-11 --pattern 'lluvia-distritos-*.json.gz'
```

```python
import gzip, json
archivo = json.loads(gzip.decompress(open("lluvia-distritos-20261123T130000Z.json.gz", "rb").read()))
```

## Contenido

| Campo                | Significado                                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------------- |
| `formato`            | Siempre `radar-nino-norte/archivo-lluvia`.                                                                      |
| `version_formato`    | `1`. Un cambio incompatible sube este número; los archivos viejos no se reescriben.                             |
| `generado_en`        | Hora UTC de la ejecución.                                                                                       |
| `version_pipeline`   | Versión del pipeline; `commit`, el commit de `main` que lo generó (o `null` en una ejecución local).            |
| `hora_corte_utc`     | `12`: cada día pluviométrico va de las 12 UTC a las 12 UTC del día siguiente (7 a. m. a 7 a. m. en Perú).       |
| `umbrales_conteo_mm` | Umbrales para los que se cuentan miembros, en orden: `[5, 10, 15, 20, 25, 30, 40, 50, 70]` en la versión M1 v1. |
| `descargados`        | Sistemas descargados en esta ejecución. Solo ellos traen `lluvia_mm`.                                           |
| `sistemas`           | Último dato conocido de cada sistema (descargado ahora o en una ejecución anterior).                            |
| `pronostico`         | El producto `lluvia/distritos.json` emitido en esta ejecución, idéntico al publicado, o `null` si no se emitió. |

Cada elemento de `sistemas`:

- `sistema` (`ecmwf_ifs`, `ecmwf_aifs`, `ncep_gefs`), `modelo` (identificador de Open-Meteo), `miembros` (control incluido), `inicializacion` (hora de la corrida), `primer_dia` (inicio del primer día completo) y `obtenido_en`.
- `celdas`: una por nodo de 0.25° pedido. `id` es el nodo (`"lat,lon"` con dos decimales); `latitud`, `longitud` y `altitud_m` son la celda que el modelo usó de verdad (puede ser vecina, y `altitud_m` 0 es mar).
- `celdas[].dias`: siete días con `inicio`, `validos` (miembros con dato), `alcanzan` (cuántos miembros válidos tienen lluvia ≥ cada umbral de `umbrales_conteo_mm`) y `lluvia_mm` (lluvia del día por miembro en mm, el 0 es el control; `null` en un miembro sin dato; la lista entera es `null` si el sistema no se descargó en esta ejecución: sus valores están en el archivo de la ejecución que lo descargó).

## Rehacer las probabilidades publicadas

Para un distrito con capital en el nodo `n`, zona `z` y día `d` de `pronostico.dias`:

1. Umbrales T1, T2, T3: `pronostico.metodo.umbrales_mm[z]`.
2. Por cada corrida de `pronostico.corridas`, busca su sistema en `sistemas`, la celda `id == n` y el día `inicio == d`. P_s(≥T) = `alcanzan[i] / validos`, con `i` la posición de T en `umbrales_conteo_mm` (o, con los valores, la fracción de miembros no nulos de `lluvia_mm` ≥ T). Si `validos` es 0 o falta el día, el sistema no cuenta ese día.
3. Mezcla: media de P_s ponderada con `pronostico.metodo.pesos`, renormalizando entre los sistemas que cuentan. Sin ningún sistema `ecmwf_*` el día no tiene dato.
4. Porcentaje publicado: `floor(100·P + 0,5)`. El nivel se decide con esos enteros y `pronostico.metodo.niveles`.

La prueba `test_archivo_ida_y_vuelta_reproduce_las_probabilidades` del pipeline hace exactamente esto.
