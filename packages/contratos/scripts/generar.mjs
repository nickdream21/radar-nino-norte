// Genera src/generado.ts a partir de los JSON Schema exportados por el pipeline.
// No editar generado.ts a mano: cambiar el contrato en pipeline/src/radar/contratos.
import { readdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileFromFile } from 'json-schema-to-typescript';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
const carpetaEsquemas = join(raiz, 'esquemas');

const archivos = (await readdir(carpetaEsquemas)).filter((a) => a.endsWith('.schema.json')).sort();

const bloques = [];
for (const archivo of archivos) {
  bloques.push(
    await compileFromFile(join(carpetaEsquemas, archivo), {
      bannerComment: '',
      additionalProperties: false,
      style: { singleQuote: true, printWidth: 100 },
    }),
  );
}

const cabecera = '// GENERADO por scripts/generar.mjs desde esquemas/*.schema.json. No editar.\n\n';
await writeFile(join(raiz, 'src', 'generado.ts'), cabecera + bloques.join('\n'));
console.log(`Tipos generados desde ${archivos.length} esquema(s).`);
