# Operación

## Flujos de GitHub Actions

| Flujo            | Cuándo                       | Qué hace                                                                               |
| ---------------- | ---------------------------- | -------------------------------------------------------------------------------------- |
| `ci.yml`         | Cada PR y cada push a `main` | Lint, tipos, pruebas y build de la web; lint, tipos y pruebas del pipeline; contratos  |
| `despliegue.yml` | Push a `main` o manual       | Construye la web, añade la rama `datos` si existe y publica en GitHub Pages            |
| `release.yml`    | Push a `main`                | release-please abre el PR de versión y, al fusionarlo, crea la etiqueta y el changelog |

Los flujos de ingesta (`ingesta-*.yml`) se añaden en la Fase 1.

## Configuración del repositorio (una sola vez)

1. Pages: _Settings → Pages → Source: GitHub Actions_.
2. Protección de `main`: exigir PR, exigir los chequeos de `ci.yml`, prohibir push directo y force-push.
3. _Settings → Actions → General → Workflow permissions_: permitir que Actions cree pull requests (lo necesita release-please).

## Versiones

Los commits `feat:` suben la versión menor y los `fix:` el parche. release-please mantiene un PR abierto con el changelog; fusionarlo publica la versión.

## Cuando una fuente falla

El pipeline conserva el último dato válido y la web lo muestra como antiguo cuando supera su `vigencia_min`. Revisar el registro del flujo de ingesta, comprobar la fuente a mano y, si cambió de formato, actualizar el adaptador y su respuesta grabada.

## Vulnerabilidades conocidas

`npm audit` informa avisos moderados en `glob` y `minimatch`, que llegan por `workbox-build` (dependencia de `vite-plugin-pwa`). Solo se ejecutan al construir, no en el navegador del usuario. Se resuelven al actualizar `vite-plugin-pwa`; Dependabot lo propondrá.

## El PR de versión no ejecuta CI por sí solo

GitHub no dispara flujos en los PR creados con el token de Actions, así que el PR de release-please queda bloqueado a la espera de los chequeos obligatorios. Para lanzarlos, cerrar y reabrir el PR:

```sh
gh pr close <número> && gh pr reopen <número>
```

Alternativa permanente: dar a release-please un token personal como secreto del repositorio.
