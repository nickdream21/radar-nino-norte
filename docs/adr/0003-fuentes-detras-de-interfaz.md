# 0003 — Toda fuente externa detrás de una interfaz

**Estado:** Aceptado (2026-11-23)

## Contexto

La app depende de servicios de terceros gratuitos que cambian sin aviso: RainViewer retiró su satélite gratuito, IRI dejó de publicar datos y CPC cambió de versión de ERSST. Open-Meteo, la fuente principal de pronósticos, solo es gratuita para uso no comercial.

## Decisión

Cada proveedor se integra como un adaptador que implementa `FuenteDatos` (`pipeline/src/radar/fuentes/base.py`) y devuelve un contrato propio ya validado. Modelos y publicación dependen de la interfaz, nunca del proveedor. Cada adaptador tiene pruebas con respuestas grabadas; las pruebas no usan la red.

Un fallo se señala con `FuenteNoDisponible`. Quien lo recibe conserva el último dato válido; nunca se rellenan valores.

## Consecuencias

- Reemplazar Open-Meteo por ECMWF Open Data o NOAA directos afecta a un adaptador, no al resto.
- Un cambio de formato en una fuente rompe una prueba concreta en lugar de corromper datos publicados.
- Cuesta algo más al principio: cada fuente necesita su contrato y su respuesta grabada.
