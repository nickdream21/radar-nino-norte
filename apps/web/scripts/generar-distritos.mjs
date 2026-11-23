// Genera src/features/mi-distrito/distritos.generado.ts a partir de
// datos-estaticos/distritos.json (contrato CatalogoDistritos), con solo lo que la web necesita
// para elegir distrito: ubigeo, nombre, provincia, departamento y la posición de la capital.
// No editar el archivo generado a mano: regenerarlo con `npm run distritos:generar`.
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const raizWeb = join(dirname(fileURLToPath(import.meta.url)), '..');
const origen = join(raizWeb, '..', '..', 'datos-estaticos', 'distritos.json');
const destino = join(raizWeb, 'src', 'features', 'mi-distrito', 'distritos.generado.ts');

const catalogo = JSON.parse(await readFile(origen, 'utf8'));

// El pipeline ya valida el catálogo completo; aquí solo se comprueba lo que se copia.
if (catalogo.version_esquema !== 1) {
  throw new Error(`version_esquema no admitida: ${catalogo.version_esquema}`);
}
const texto = (valor, campo, ubigeo) => {
  if (typeof valor !== 'string' || valor.trim() === '') {
    throw new Error(`Distrito ${ubigeo}: ${campo} vacío o no es texto`);
  }
  return valor;
};
const numero = (valor, campo, ubigeo, limite) => {
  if (typeof valor !== 'number' || !Number.isFinite(valor) || Math.abs(valor) > limite) {
    throw new Error(`Distrito ${ubigeo}: ${campo} no es una coordenada válida`);
  }
  return valor;
};

const vistos = new Set();
const filas = catalogo.distritos
  .map((d) => {
    if (!/^\d{6}$/.test(d.ubigeo)) throw new Error(`Ubigeo no válido: ${d.ubigeo}`);
    if (vistos.has(d.ubigeo)) throw new Error(`Ubigeo repetido: ${d.ubigeo}`);
    vistos.add(d.ubigeo);
    return [
      d.ubigeo,
      texto(d.nombre, 'nombre', d.ubigeo),
      texto(d.provincia, 'provincia', d.ubigeo),
      texto(d.departamento, 'departamento', d.ubigeo),
      numero(d.capital?.latitud, 'capital.latitud', d.ubigeo, 90),
      numero(d.capital?.longitud, 'capital.longitud', d.ubigeo, 180),
    ];
  })
  // Orden estable por ubigeo: el diff solo cambia cuando cambia el catálogo.
  .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));

const lineas = filas.map((fila) => `  ${JSON.stringify(fila)},`);
const contenido = `// GENERADO por apps/web/scripts/generar-distritos.mjs desde datos-estaticos/distritos.json.
// No editar: regenerar con \`npm run distritos:generar\`.
// Datos: INEI (RENAMU 2026, ODC-By 1.0; Censos Nacionales 2017), GeoNames (CC BY 4.0) y
// Wikidata (CC0); procedencia completa en datos-estaticos/README.md.
import type { FilaDistrito } from './catalogo';

/** [ubigeo, nombre, provincia, departamento, latitud, longitud de la capital] */
export const FILAS_DISTRITOS: readonly FilaDistrito[] = [
${lineas.join('\n')}
];
`;

await writeFile(destino, contenido);
console.log(`Lista de distritos generada: ${filas.length} distritos.`);
