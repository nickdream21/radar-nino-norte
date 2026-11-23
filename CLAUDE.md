# Radar Niño Norte — reglas del proyecto

PWA gratuita, sin anuncios y de código abierto sobre El Niño costero para el público general del norte del Perú. Costo de infraestructura: cero. Responder al usuario en español.

Leer antes de trabajar: `docs/arquitectura.md`, `docs/fuentes-de-datos.md` y los ADR en `docs/adr/`.

## Reparto de modelos

- **Fable** (sesión principal): análisis, planes y revisión.
- **Opus** (subagentes ejecutores): escritura de código.

Flujo por tarea: Fable escribe un plan corto con criterios de aceptación → delega a `ingeniero-datos`, `cientifico-modelos`, `frontend-mapas` o `devops-calidad` → Fable revisa el resultado contra el plan antes del PR. `meteorologo-enso` y `ux-contenido` asesoran y revisan; no escriben código.

## Arquitectura en una línea

Fuentes abiertas → `pipeline` (Python, cron de GitHub Actions) → productos JSON estáticos en la rama `datos` → `apps/web` los lee. No hay servidor propio. No añadir uno sin un ADR.

## Reglas de código

- Los contratos de datos se definen **solo** en `pipeline/src/radar/contratos` (pydantic). Los esquemas JSON y los tipos TypeScript se generan; nunca se editan a mano.
- Toda fuente externa va detrás de la interfaz `FuenteDatos` (`pipeline/src/radar/fuentes/base.py`) y tiene pruebas con respuestas grabadas. Las pruebas no llaman a la red.
- Si una fuente falla, el pipeline publica el último dato válido con su antigüedad; nunca inventa ni rellena valores.
- Nombres de dominio en español, sin tildes ni ñ en identificadores, archivos y rutas.
- TypeScript estricto; Python con `mypy --strict` y `ruff`.
- Antes de añadir una dependencia: comprobar que no se resuelve con lo ya instalado y justificarla en el PR.
- Los textos para el público hablan en probabilidades y lenguaje simple, sin alarmismo, y nunca se presentan como alerta oficial.

## Git y entrega

- `main` protegida. Ramas `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- Conventional Commits en español (`feat(pipeline): …`). release-please genera versiones y `CHANGELOG.md`.
- Los commits hechos a mano tienen como único autor al dueño del repositorio: sin líneas `Co-Authored-By`, sin firmas ni menciones de herramientas en commits ni en PR. Los robots de GitHub (Dependabot, release-please) sí pueden fusionarse.
- Todo cambio entra por PR con CI en verde y squash merge.
- Cada decisión estructural se registra como ADR nuevo en `docs/adr/` (no se reescriben los anteriores; se reemplazan con uno nuevo).
- Un modelo predictivo solo reemplaza a su versión anterior si la supera en las métricas de verificación archivadas.

## Comandos

```sh
npm run lint && npm run typecheck && npm test && npm run build
cd pipeline && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

Regenerar contratos: ver README.
