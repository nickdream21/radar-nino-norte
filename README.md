# Radar Niño Norte

PWA gratuita y de código abierto para seguir El Niño costero en el norte del Perú (Tumbes, Piura, Lambayeque, La Libertad y Cajamarca): lluvia probable por distrito, rayos, estado de El Niño y ríos.

> **No es una fuente oficial de alertas.** Los avisos oficiales los emiten [SENAMHI](https://www.senamhi.gob.pe/?p=aviso-meteorologico) y ENFEN.

## Estado

Fase 0 (cimientos). El plan por fases está en [docs/arquitectura.md](docs/arquitectura.md).

## Estructura

| Carpeta              | Contenido                                                           |
| -------------------- | ------------------------------------------------------------------- |
| `apps/web`           | PWA (React, TypeScript, Vite)                                       |
| `pipeline`           | Ingesta, modelos y publicación de productos (Python, uv)            |
| `packages/contratos` | Esquemas JSON y tipos TypeScript generados desde el pipeline        |
| `docs`               | Arquitectura, fuentes de datos, operación y decisiones (`docs/adr`) |
| `.claude/agents`     | Subagentes especializados del proyecto                              |

## Requisitos

- Node 24 o superior
- Python 3.12 y [uv](https://docs.astral.sh/uv/)

## Uso

```sh
npm install            # dependencias web
npm run dev            # servidor de desarrollo
npm run lint && npm run typecheck && npm test

cd pipeline
uv sync                # dependencias del pipeline
uv run pytest
uv run radar publicar --destino ../apps/web/public/datos   # genera productos locales
```

Al cambiar un contrato en `pipeline/src/radar/contratos`:

```sh
cd pipeline && uv run radar exportar-esquemas --destino ../packages/contratos/esquemas
cd .. && npm run contratos:generar
```

## Cómo contribuir

Ramas `feat/…` o `fix/…`, [Conventional Commits](https://www.conventionalcommits.org/es/), PR con CI en verde. Las reglas completas están en [CLAUDE.md](CLAUDE.md).

## Licencia

Código bajo [MIT](LICENSE). Los datos conservan la licencia de cada fuente; ver [docs/fuentes-de-datos.md](docs/fuentes-de-datos.md).
