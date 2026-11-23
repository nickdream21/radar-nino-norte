# Arquitectura

## Propósito

PWA gratuita, sin anuncios y de código abierto para el público general de Tumbes, Piura, Lambayeque, La Libertad y Cajamarca. Reúne en un solo lugar la lluvia probable por distrito, los rayos, el estado de El Niño costero y los ríos. Costo de infraestructura: cero.

## Vista general

```
Fuentes abiertas ──> pipeline (Python, cron de GitHub Actions) ──> productos JSON en la rama `datos` ──> PWA
Capas listas para navegador (NASA GIBS, NOAA nowCOAST, OpenFreeMap) ──────────────────────────────────> PWA
```

No hay servidor propio ([ADR 0001](adr/0001-sin-servidor-propio.md)).

| Capa      | Carpeta              | Responsabilidad                                                              |
| --------- | -------------------- | ---------------------------------------------------------------------------- |
| Pipeline  | `pipeline`           | Leer fuentes, validar, aplicar modelos y escribir productos y el manifiesto  |
| Contratos | `packages/contratos` | Esquemas JSON y tipos TypeScript generados desde pydantic                    |
| Web       | `apps/web`           | Leer el manifiesto y los productos, mostrarlos y guardarlos para uso sin red |

### Pipeline

- `contratos/`: modelos pydantic, única fuente de verdad ([ADR 0005](adr/0005-contratos-generados.md)).
- `fuentes/`: un adaptador por proveedor detrás de `FuenteDatos` ([ADR 0003](adr/0003-fuentes-detras-de-interfaz.md)).
- `modelos/` (desde la Fase 1): M1 lluvia, M2 tormentas, M3 El Niño y la verificación.
- `publicacion/`: escritura atómica de productos y del `manifiesto.json`.

Si una fuente falla se conserva el último dato válido con su antigüedad. Nunca se rellenan valores.

### Web

Organizada por funcionalidad en `apps/web/src/features/`. La web lee primero `datos/manifiesto.json`, que indica qué productos existen y cuándo se actualizaron; cada producto declara su `vigencia_min` para que la interfaz lo marque como antiguo. El service worker sirve los datos con estrategia "red primero" y cae al último dato guardado sin conexión.

### Publicación

Los productos se escriben en la rama huérfana `datos` y el despliegue los copia a `/datos/` del sitio de GitHub Pages ([ADR 0002](adr/0002-publicacion-en-rama-datos.md)).

## Modelos propios

No se entrena un modelo global: se combinan y corrigen localmente los mejores disponibles.

| Modelo                         | Versión inicial                                                      | Evolución                                                    |
| ------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------ |
| M1 lluvia por distrito, 0–10 d | Mezcla de ensambles (ECMWF IFS/AIFS, GEFS) → P(>10 / 30 / 60 mm/día) | Corrección por cuantiles contra CHIRPS/IMERG; luego LightGBM |
| M2 tormentas                   | Probabilidad a 48 h desde CAPE y lluvia de los miembros              | Destellos GLM de los últimos 30 min + vector de movimiento   |
| M3 El Niño costero             | Índices observados + penacho Niño 1+2 de SEAS5                       | Red propia solo como capa experimental                       |

Cada pronóstico emitido se archiva y se compara a diario con lo observado (Brier, fiabilidad, sesgo). Una versión nueva solo reemplaza a la anterior si la supera.

### Límites conocidos

- Sin radar público en el norte, el aviso de tormenta es fiable a 1–2 horas.
- El pronóstico de El Niño costero a meses tiene poca precisión en todo el mundo.
- La mejora sobre los modelos globales es de calibración local, no de física.

## Fases

| Fase | Versión | Contenido                                                                                     |
| ---- | ------- | --------------------------------------------------------------------------------------------- |
| 0    | v0.1.0  | Repositorio, CI, despliegue, contratos, subagentes, ADR                                       |
| 1    | v0.2.0  | Mapa (satélite, lluvia, rayos nowCOAST), semáforo por distrito (M1 v1), termómetro de El Niño |
| 2    | v0.3.0  | Ríos con umbrales, página de acierto, comparación con 1983/1998/2017/2023                     |
| 3    | v0.4.0  | Rayos GLM propios, "rayos a X km de ti", probabilidad de tormenta 48 h                        |
| 4    | v0.5.0  | M1 v2 (cuantiles), notificaciones push                                                        |
| 5    | v1.0.0  | M1 v3 (LightGBM), M3 experimental, adaptador directo a ECMWF Open Data                        |

## Riesgos

| Riesgo                                   | Mitigación                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------- |
| Open-Meteo es solo para uso no comercial | Interfaz reemplazable; pedir confirmación por escrito en la Fase 4      |
| Cuota de 10 000 llamadas al día          | Ensambles por rejilla de 0.25° asignada a distritos; presupuesto medido |
| El cron de GitHub Actions se retrasa     | nowCOAST directo en el navegador como respaldo de rayos                 |
| El HTML de avisos de SENAMHI cambia      | Prueba con HTML grabado y degradación a solo enlace                     |
| Licencia de los límites distritales      | Usar fuente oficial INEI/IGN y verificar la licencia al descargar       |
