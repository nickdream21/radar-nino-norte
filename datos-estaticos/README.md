# Datos estáticos

Datos sin formato legible por máquina que se mantienen a mano. El pipeline los valida al publicar: si un archivo no cumple su contrato, el bloque correspondiente se trata como fuente caída.

## `enfen.json`

Último comunicado oficial del ENFEN (contrato `ComunicadoEnfen` en `pipeline/src/radar/contratos/nino.py`).

| Campo    | Contenido                                                                     |
| -------- | ----------------------------------------------------------------------------- |
| `estado` | Estado del sistema de alerta, copiado tal cual del comunicado                 |
| `numero` | Número del comunicado, `NN-AAAA`                                              |
| `fecha`  | Fecha de emisión con zona horaria de Lima, p. ej. `2026-11-13T00:00:00-05:00` |
| `enlace` | Dirección del comunicado (PDF) o, si no se tiene, del sitio del ENFEN         |

Actualizarlo cada vez que el ENFEN emita un comunicado (habitualmente cada dos semanas). La fecha se publica para que la web pueda avisar cuando el comunicado sea antiguo.
