# 0004 — React, Vite, MapLibre y PWA

**Estado:** Aceptado (2026-11-23)

## Contexto

El público usa sobre todo celulares Android de gama media o baja, con conexión irregular. La app es un mapa con capas de tiempo más unas pocas pantallas de lectura. Debe poder instalarse sin pasar por tiendas y sin claves de pago.

## Decisión

- **React 19 + TypeScript estricto + Vite**: el ecosistema con más documentación y personas capaces de mantenerlo.
- **MapLibre GL JS** con mapa base de **OpenFreeMap**: libres, sin clave y sin límites de uso.
- **vite-plugin-pwa (Workbox)**: instalable y con caché sin conexión; los datos usan "red primero".
- **Tailwind CSS 4** para estilos; **Vitest + Testing Library** para pruebas; **Playwright** para los flujos principales desde la Fase 1.
- **npm workspaces**, sin gestor de monorepo adicional.

Se añadirán cuando hagan falta, no antes: TanStack Query (cuando haya varios productos que refrescar) y uPlot (primeras gráficas).

## Consecuencias

- Una sola base de código para web y celular; sin costos de tienda.
- En iOS las PWA tienen limitaciones en notificaciones push; se evaluará en la Fase 4.
- MapLibre pesa en el primer arranque: se cargará de forma diferida y se vigilará el tamaño del paquete en CI.
