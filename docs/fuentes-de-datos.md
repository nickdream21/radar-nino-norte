# Fuentes de datos

Resultado de la investigación del 23-nov-2026. "Verificado" significa que el punto de acceso respondió con datos reales ese día. Antes de construir un adaptador, volver a comprobar la fuente y grabar una respuesta para las pruebas.

## En uso o planificadas

| Producto                           | Fuente y acceso                                                                                                                                                      | Notas                                                                                                          |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Pronóstico determinista            | Open-Meteo `api.open-meteo.com/v1/forecast` (`ecmwf_ifs`, `ecmwf_ifs025`, `ecmwf_aifs025_single`, `gfs_seamless`, `icon_global`)                                     | Verificado. `gfs_graphcast025` devuelve nulos                                                                  |
| Ensambles                          | Open-Meteo `ensemble-api.open-meteo.com/v1/ensemble` (`ecmwf_ifs025_ensemble`, `ecmwf_aifs025_ensemble`, `ncep_gefs025`)                                             | Verificado. Las llamadas pesan más de 1. `google_weathernext2_ensemble` figura en la documentación, sin probar |
| Convección                         | Open-Meteo `cape`, `convective_inhibition`, `lifted_index`                                                                                                           | Verificado con GFS. En ECMWF solo `cape`. `lightning_potential` y datos reales de 15 min no existen para Perú  |
| Caudales                           | Open-Meteo Flood (GloFAS v4)                                                                                                                                         | Verificado en Tumbes–El Tigre (−3.769, −80.457). Piura y Chira requieren elegir la celda a mano                |
| Estacional                         | Open-Meteo `seasonal-api.open-meteo.com/v1/seasonal` (SEAS5, 51 miembros, incluye temperatura del mar)                                                               | Solo documentación                                                                                             |
| Niño 1+2, 3.4 semanales            | NOAA CPC `https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for`                                                                                                  | Verificado. Texto de ancho fijo, sin CORS                                                                      |
| ONI, RONI                          | NOAA CPC `oni.ascii.txt`, `RONI.ascii.txt` (misma carpeta)                                                                                                           | Verificado. No usar `ersst5.nino.mth.91-20.ascii` (detenido en junio de 2026)                                  |
| Contenido de calor                 | NOAA CPC `…/products/analysis_monitoring/ocean/index/heat_content_index.txt`                                                                                         | Verificado                                                                                                     |
| ICEN                               | IGP `http://met.igp.gob.pe/datos/ICEN.txt`                                                                                                                           | Verificado. Solo HTTP y sensible a mayúsculas                                                                  |
| Anomalía del mar frente a la costa | Coral Reef Watch 5 km, ERDDAP PacIOOS `pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km`                                                                           | Verificado. 2 días de retraso; puntos pegados a la costa devuelven NaN                                         |
| Rayos (Fase 1)                     | NOAA nowCOAST WMS, capa `ldn_lightning_strike_density`                                                                                                               | Verificado. Cada 15 min, CORS abierto, cubre de 25° S a 80° N. Ver nota 1                                      |
| Rayos (Fase 3)                     | GOES-19 GLM `https://noaa-goes19.s3.amazonaws.com/?list-type=2&prefix=GLM-L2-LCFA/AAAA/DDD/HH/`                                                                      | Verificado el listado. Un archivo cada 20 s, ~30 s de retraso, sin CORS; estructura NetCDF sin abrir           |
| Satélite, lluvia y mar en mapa     | NASA GIBS WMTS: `GOES-East_ABI_Band13_Clean_Infrared`, `GOES-East_ABI_GeoColor`, `IMERG_Precipitation_Rate_30min`, `GHRSST_L4_MUR_Sea_Surface_Temperature_Anomalies` | Verificado. Sin clave. Infrarrojo con 30–65 min de retraso; IMERG con unas 5 h. Ver nota 2                     |
| Avisos oficiales                   | SENAMHI `https://www.senamhi.gob.pe/?p=aviso-meteorologico`                                                                                                          | Verificado. Tabla HTML, sin API                                                                                |
| Estado ENFEN                       | Comunicados en PDF                                                                                                                                                   | Sin formato legible por máquina: se mantiene a mano en `datos-estaticos`                                       |
| Verdad para verificar y entrenar   | CHIRPS v3 `https://data.chc.ucsb.edu/products/CHIRPS/v3.0/`, IMERG (token Earthdata), ERA5 vía Open-Meteo                                                            | CHIRPS verificado, ~3 días de retraso                                                                          |
| Archivo de pronósticos pasados     | Open-Meteo Historical Forecast y Previous Runs                                                                                                                       | IFS 9 km desde 2017; el resto desde 2021–2025                                                                  |
| Mapa base                          | OpenFreeMap                                                                                                                                                          | Sin clave ni límites; requiere atribución                                                                      |

### Hora de las capas del mapa (comprobado el 23-nov-2026, 14:40 UTC)

1. **nowCOAST**: el `GetCapabilities` (10 kB, caché de 10 min) lista en `<Dimension name="time">` las últimas 6 h cada 15 min; la última estaba 25 min por detrás de la hora real. Un `GetMap` con una hora inexistente no da error: devuelve la más cercana (`nearestValue="1"`), así que la web siempre pide una hora tomada del listado.
2. **GIBS**: el `GetCapabilities` completo pesa 5,8 MB; para el navegador se usa `DescribeDomains` (`…/1.0.0/{capa}/default/GoogleMapsCompatible_Level6/all/{desde}--{hasta}.xml`, < 1 kB, CORS abierto, caché de 30 min). Infrarrojo: entre 30 y 50 min de retraso a lo largo de la prueba. IMERG: 08:30–09:30 UTC (unas 5 h), con huecos en su historial. Las teselas llevan la hora en la ruta: `…/{capa}/default/{hora}/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png`.

### Detalles comprobados al construir los adaptadores

Comprobado el 23-nov-2026 al programar `pipeline/src/radar/fuentes/`. Las respuestas grabadas están en `pipeline/tests/fixtures/`.

- **NOAA CPC semanal**: responde sin cabecera `Content-Type`. La fecha es el día central de la semana. Las anomalías negativas quedan pegadas a la temperatura (`20.6-0.1`). La semana nueva aparece el lunes durante el día.
- **ICEN**: cuatro líneas de cabecera con `%` antes de `% yy mm ICEN`. Es una media móvil de tres meses centrada en el mes indicado, así que el último valor va unos dos meses por detrás (en noviembre, septiembre).
- **Coral Reef Watch (ERDDAP)**: la latitud va de norte a sur, aunque ERDDAP 2.29 acepta el rango en ambos sentidos. Las celdas sin dato llegan como `null` en `.json` (`_FillValue` −327.68). Un error de consulta responde HTTP 500 con texto `Error {…}`, no JSON.
- **ENFEN**: `enfen.imarpe.gob.pe` responde 403 con un desafío de Cloudflare a clientes automáticos; los comunicados solo se pueden leer desde un navegador.

## Condiciones de uso

- **Open-Meteo**: gratuito solo para uso no comercial; menos de 10 000 llamadas al día, 5 000 por hora y 600 por minuto. Datos CC BY 4.0.
- **NOAA y NASA**: datos abiertos; se atribuye la fuente.
- **ECMWF Open Data**: CC BY 4.0, permite uso comercial. Es la alternativa si Open-Meteo deja de ser viable.

## Descartadas

| Fuente                             | Motivo                                                           |
| ---------------------------------- | ---------------------------------------------------------------- |
| Datos de estaciones SENAMHI        | Protegidos por captcha                                           |
| PISCO en tiempo real               | Actualizaciones suspendidas; el histórico exige inicio de sesión |
| ANA (caudales)                     | Sin servicios en tiempo real para Tumbes, Chira ni Piura         |
| RainViewer                         | Quitó satélite y pronóstico gratuitos en enero de 2026           |
| Blitzortung / LightningMaps        | Datos solo para quienes operan una estación                      |
| Rayos de Xweather, Tomorrow.io     | De pago                                                          |
| Penacho de IRI                     | Ya no publica datos, solo imágenes                               |
| Radares de Piura (ANIN, UDEP, IGP) | Sin acceso público; gestionar con SENAMHI Dirección Zonal 1      |
