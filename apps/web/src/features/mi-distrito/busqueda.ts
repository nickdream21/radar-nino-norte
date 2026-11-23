import { compararTexto, type DistritoLista } from './catalogo';

/**
 * Forma comparable de un texto: sin tildes (la ñ queda como n), en minúsculas, con cualquier
 * signo convertido en espacio y sin espacios de más.
 */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

interface Entrada {
  distrito: DistritoLista;
  /** Nombre normalizado. */
  nombre: string;
  /** Nombre y provincia normalizados con un espacio delante: " santa rosa". */
  palabrasNombre: string;
  palabrasProvincia: string;
}

/** Lista ya normalizada: se prepara una sola vez, no en cada tecla. */
export interface IndiceBusqueda {
  readonly entradas: readonly Entrada[];
}

export function prepararIndice(distritos: readonly DistritoLista[]): IndiceBusqueda {
  return {
    entradas: distritos.map((distrito) => {
      const nombre = normalizar(distrito.nombre);
      return {
        distrito,
        nombre,
        palabrasNombre: ` ${nombre}`,
        palabrasProvincia: ` ${normalizar(distrito.provincia)}`,
      };
    }),
  };
}

/**
 * Prioridad de una coincidencia (menor es mejor) o `null` si no coincide:
 * 0, el nombre es exactamente lo escrito; 1, el nombre empieza por ello; 2, alguna palabra del
 * nombre empieza por ello; 3, la provincia (alguna de sus palabras) empieza por ello.
 */
function prioridad(entrada: Entrada, consulta: string): number | null {
  if (entrada.nombre === consulta) return 0;
  if (entrada.nombre.startsWith(consulta)) return 1;
  if (entrada.palabrasNombre.includes(` ${consulta}`)) return 2;
  if (entrada.palabrasProvincia.includes(` ${consulta}`)) return 3;
  return null;
}

/**
 * Distritos que coinciden con lo escrito, los más parecidos primero y, a igual prioridad, en
 * orden alfabético. Por tecla solo se normaliza la consulta.
 */
export function buscar(indice: IndiceBusqueda, texto: string): DistritoLista[] {
  const consulta = normalizar(texto);
  if (consulta === '') return [];
  const encontrados: { distrito: DistritoLista; prioridad: number }[] = [];
  for (const entrada of indice.entradas) {
    const valor = prioridad(entrada, consulta);
    if (valor !== null) encontrados.push({ distrito: entrada.distrito, prioridad: valor });
  }
  return encontrados
    .sort(
      (a, b) =>
        a.prioridad - b.prioridad ||
        compararTexto(a.distrito.nombre, b.distrito.nombre) ||
        compararTexto(a.distrito.provincia, b.distrito.provincia),
    )
    .map((e) => e.distrito);
}
