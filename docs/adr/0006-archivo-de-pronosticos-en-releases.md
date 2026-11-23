# 0006 — Archivo de pronósticos emitidos en GitHub Releases

**Estado:** Aceptado (2026-11-23)

## Contexto

Cada pronóstico de lluvia emitido (M1) debe guardarse desde el primer día para verificarlo contra lo observado (Brier, fiabilidad, sesgo) y, más adelante, calibrarlo. Hacen falta los valores por miembro de cada sistema, no solo las probabilidades publicadas: sin ellos no se puede probar otro umbral, otro peso ni una corrección por cuantiles.

Una ejecución que descarga los tres sistemas produce un archivo de unos 190 kB comprimido (815 kB sin comprimir; 117 celdas, 7 días, 133 miembros, medido el 23-nov-2026). Como cada sistema llega a Open-Meteo a una hora distinta, el plan de descargas (ver `docs/operacion.md`) genera hasta cuatro archivos al día, del orden de 10 MB al mes. La rama `datos` se reemplaza en cada ejecución sin historial ([ADR 0002](0002-publicacion-en-rama-datos.md)), así que no sirve para guardar nada que deba durar.

## Decisión

Cada archivo se sube como activo (_asset_) de un release de GitHub, uno por mes, con etiqueta `archivo-pronosticos-AAAA-MM`, marcado como _prerelease_ y creado con `--latest=false`. Lo sube el flujo `ingesta-horaria.yml` con el `GITHUB_TOKEN`.

- El pipeline no habla con GitHub: escribe los archivos en `archivo-pendiente/` dentro de la publicación y el flujo los sube y, si la subida sale bien, los borra antes de publicar `datos`.
- Si la subida falla, el pronóstico se publica igual, el paso deja un error visible en el registro y el archivo queda en `archivo-pendiente/` (dentro de `datos`) para reintentarlo en la ejecución siguiente. El pipeline conserva como mucho los 20 más recientes.
- El formato es JSON comprimido con gzip, versionado (`formato`, `version_formato`) y con esquema publicado en `docs/esquemas/archivo_lluvia.schema.json`; se describe en [`docs/archivo-pronosticos.md`](../archivo-pronosticos.md) para poder leerlo sin el código del pipeline.

## Alternativas descartadas

- **Una rama de git con historial:** cada archivo binario quedaría para siempre en el historial; cualquier clon del repositorio crecería del orden de 100 MB al año, y más si se añaden variables.
- **La rama `datos`:** se reemplaza en cada ejecución con force-push; lo que no se vuelve a escribir desaparece, y todo lo que contiene se despliega en Pages.
- **Artefactos de GitHub Actions:** caducan (90 días como máximo en repositorios públicos) y cuentan para el almacenamiento de Actions.
- **Un almacenamiento externo (R2, S3, Zenodo):** exige cuentas y secretos adicionales; queda como ruta de salida.

## Consecuencias

- Coste cero, sin cuentas ni secretos nuevos y sin hacer crecer el repositorio: los activos de un release no forman parte del historial de git.
- Límites de GitHub conocidos: 2 GiB por archivo y 1 000 activos por release; con un release al mes se usan hasta unos 125 activos. No hay tope publicado de tamaño total, pero GitHub puede pedir moderar un uso abusivo; si llegara a pasar, la salida es un almacenamiento de objetos externo.
- Las etiquetas `archivo-pronosticos-*` conviven con las de release-please (`radar-nino-norte-v*`): release-please solo considera las etiquetas que coinciden con su patrón de componente y versión, y los releases de archivo son _prerelease_ y se crean con `--latest=false`, así que nunca pasan a ser el "latest" del repositorio.
- La creación de una etiqueta con el `GITHUB_TOKEN` no dispara otros flujos.
- Un archivo perdido (subida fallida más de 20 veces seguidas) deja un hueco en la verificación, visible por la ausencia del nombre en el release del mes.
- La pestaña _Releases_ del repositorio mostrará estos prereleases junto a las versiones de la aplicación.
