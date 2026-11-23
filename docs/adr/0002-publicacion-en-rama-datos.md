# 0002 — Productos publicados en la rama `datos`

**Estado:** Aceptado (2026-11-23)

## Contexto

Los productos del pipeline necesitan un alojamiento gratuito, con HTTPS y sin cuentas adicionales. Guardarlos en `main` llenaría el historial de commits automáticos.

## Decisión

El pipeline escribe los productos en una rama huérfana `datos`, reemplazada en cada ejecución con force-push para que no acumule historial. El flujo de despliegue copia esa rama a `/datos/` del sitio de GitHub Pages. La web empieza siempre por `datos/manifiesto.json`.

`datos` es la única rama donde se permite force-push, y solo desde los flujos de ingesta.

## Consecuencias

- Todo vive en GitHub: un solo proveedor y una sola cuenta.
- Cada actualización de datos implica un despliegue de Pages; hay un límite orientativo de 10 por hora y 100 GB de tráfico al mes.
- El archivo histórico de pronósticos para la verificación no cabe en este esquema sin historial: se decidirá su almacenamiento en la Fase 1.
- Ruta de salida si se alcanzan los límites: servir los productos desde Cloudflare R2, cambiando solo la URL base de datos en la web y el paso de publicación.
