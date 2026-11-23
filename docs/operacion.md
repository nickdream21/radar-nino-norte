# Operación

## Flujos de GitHub Actions

| Flujo                 | Cuándo                                         | Qué hace                                                                               |
| --------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| `ci.yml`              | Cada PR y cada push a `main`                   | Lint, tipos, pruebas y build de la web; lint, tipos y pruebas del pipeline; contratos  |
| `despliegue.yml`      | Push a `main`, manual o llamado por la ingesta | Construye la web, añade la rama `datos` si existe y publica en GitHub Pages            |
| `release.yml`         | Push a `main`                                  | release-please abre el PR de versión y, al fusionarlo, crea la etiqueta y el changelog |
| `ingesta-horaria.yml` | Cada hora en el minuto 17 (UTC) o manual       | Ejecuta `radar publicar`, reemplaza la rama `datos` y despliega la página              |

## Ingesta horaria (`ingesta-horaria.yml`)

Implementa el [ADR 0002](adr/0002-publicacion-en-rama-datos.md). Pasos del job `ingerir`:

1. Descarga la rama `datos` (si existe) en una carpeta temporal. Es la publicación anterior: el pipeline la usa para conservar el último dato válido de una fuente que falla.
2. Ejecuta `uv run radar publicar --destino <carpeta>` desde `pipeline/`.
3. Comprueba que existe `manifiesto.json` y que es JSON válido.
4. Crea un commit huérfano (sin padres) con el contenido de la carpeta y lo sube a `datos` con `git push --force-with-lease`. Si el contenido es idéntico a lo publicado, no sube nada ni despliega.

Después, el job `desplegar` llama a `despliegue.yml` como flujo reutilizable (`workflow_call`). Se eligió así, y no un disparo con `gh workflow run`, porque un push hecho con `GITHUB_TOKEN` no lanza otros flujos, y la llamada reutilizable no necesita el permiso `actions: write` y deja la ingesta y su despliegue en una misma ejecución: si el despliegue falla, la ingesta sale en rojo.

**Permisos.** El flujo no tiene permisos por defecto (`permissions: {}`). `ingerir`: `contents: write`, solo para subir `datos`. `desplegar`: `contents: read`, `pages: write` e `id-token: write`, los mismos que el despliegue normal. No usa secretos propios; solo el `GITHUB_TOKEN` de cada ejecución.

**Garantías.**

- Si el pipeline o la comprobación del manifiesto fallan, el job termina en rojo antes de publicar: `datos` y la página siguen con lo anterior.
- `concurrency: datos` sin cancelación: una ejecución retrasada espera a que termine la anterior. Todo flujo que escriba en `datos` debe usar ese mismo grupo.
- `--force-with-lease` rechaza el push si `datos` cambió desde que se leyó la publicación anterior; la ejecución falla sin pisar nada y la siguiente parte del estado nuevo.
- Repetir una ejecución es seguro: vuelve a partir de lo publicado. Si solo falló el despliegue, basta con _Re-run failed jobs_.
- El pipeline recibe la publicación anterior completa y decide qué conserva; un archivo que deje de generar seguirá publicado mientras no lo borre.

**Lanzarlo a mano:** _Actions → Ingesta horaria → Run workflow_, o `gh workflow run ingesta-horaria.yml --ref main`. GitHub solo ejecuta los flujos programados y manuales que están en `main`, y puede retrasar o saltarse ejecuciones del cron en horas de carga. En un repositorio sin actividad durante 60 días GitHub desactiva los flujos programados; se reactivan desde la pestaña _Actions_.

## Configuración del repositorio (una sola vez)

1. Pages: _Settings → Pages → Source: GitHub Actions_.
2. Protección de `main`: exigir PR, exigir los chequeos de `ci.yml`, prohibir push directo y force-push.
   La rama `datos` no se protege: la ingesta la reemplaza con force-push. Si alguna vez se protege, hay que permitir el force-push a `github-actions[bot]`.
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
