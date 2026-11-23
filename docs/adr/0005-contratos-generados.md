# 0005 — Contratos definidos en pydantic y tipos generados

**Estado:** Aceptado (2026-11-23)

## Contexto

El pipeline (Python) y la web (TypeScript) solo se comunican mediante archivos JSON. Si cada lado describe esos archivos por su cuenta, tarde o temprano divergen y el fallo aparece en el celular del usuario.

## Decisión

Los contratos se definen una sola vez como modelos pydantic en `pipeline/src/radar/contratos` y se registran en `CONTRATOS`. De ahí se generan:

1. Esquemas JSON (`radar exportar-esquemas`) en `packages/contratos/esquemas`.
2. Tipos TypeScript (`npm run contratos:generar`) en `packages/contratos/src/generado.ts`.

Ambos resultados se versionan. CI los regenera y falla si difieren de lo confirmado. Los esquemas se exportan en modo serialización: describen lo que el pipeline escribe, de modo que los campos con valor por defecto son obligatorios para la web.

Todo contrato lleva `version_esquema`. Un cambio incompatible sube ese número y la web debe seguir aceptando la versión anterior hasta que el pipeline deje de publicarla.

## Consecuencias

- Un cambio de contrato que rompa la web falla en el chequeo de tipos, antes de publicarse.
- Los archivos generados no se editan a mano.
- La web valida en ejecución solo lo imprescindible (versión y forma básica); la validación completa ocurre al escribir, en el pipeline.
