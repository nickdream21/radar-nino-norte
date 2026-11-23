# 0001 — Sin servidor propio

**Estado:** Aceptado (2026-11-23)

## Contexto

El presupuesto es cero y el equipo es una persona. La app debe seguir funcionando durante picos de uso, que coinciden con las emergencias. Casi todos los datos cambian cada 10 minutos o más despacio.

## Decisión

No se opera ningún servidor ni base de datos. Un pipeline programado en GitHub Actions genera archivos estáticos que la web lee directamente. Las capas que ya existen como servicios de mapas abiertos (NASA GIBS, NOAA nowCOAST) se consumen desde el navegador.

## Consecuencias

- Sin costo, sin guardias y sin superficie de ataque propia; un pico de tráfico lo absorbe la CDN.
- No hay datos por usuario en el servidor. Las notificaciones push necesitarán una pieza mínima aparte (Fase 4, con su propio ADR).
- La frescura depende del cron de GitHub Actions, que puede retrasarse. Los datos que exigen segundos de latencia (rayos GLM) requieren decidir dónde ejecutarse (ADR en la Fase 3).
- El repositorio debe ser público para que los minutos de Actions sean ilimitados.
