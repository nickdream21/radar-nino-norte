import type { Manifiesto, ProductoPublicado } from '@radar/contratos';

const VERSION_ESQUEMA_SOPORTADA = 1;

export const RAIZ_DATOS = `${import.meta.env.BASE_URL}datos/`;

/** Un producto del manifiesto junto con su contenido ya validado. */
export interface Copia<T> {
  producto: ProductoPublicado;
  datos: T;
}

/** Resultado de una consulta. Distingue la falta de red de los demás fallos. */
export type Resultado<T> =
  | { tipo: 'listo'; copia: Copia<T> }
  | { tipo: 'sin-datos' }
  | { tipo: 'sin-conexion' }
  | { tipo: 'error' };

export type Validador<T> = (datos: unknown) => datos is T;

type Lectura = { tipo: 'json'; datos: unknown } | { tipo: 'no-existe' } | { tipo: 'sin-conexion' };

class ErrorDatos extends Error {}

async function leerJson(url: string, buscar: typeof fetch): Promise<Lectura> {
  let respuesta: Response;
  try {
    respuesta = await buscar(url, { cache: 'no-cache' });
  } catch {
    // `fetch` solo rechaza cuando la petición no llega a ninguna parte: falta de red.
    return { tipo: 'sin-conexion' };
  }
  if (respuesta.status === 404) return { tipo: 'no-existe' };
  if (!respuesta.ok) throw new ErrorDatos(`${url} respondió ${respuesta.status}`);
  // Sin datos publicados, un servidor estático puede devolver la página HTML en vez de un 404.
  if (!respuesta.headers.get('content-type')?.includes('json')) return { tipo: 'no-existe' };
  return { tipo: 'json', datos: await respuesta.json() };
}

export function esManifiesto(datos: unknown): datos is Manifiesto {
  if (typeof datos !== 'object' || datos === null) return false;
  const candidato = datos as Record<string, unknown>;
  return (
    candidato.version_esquema === VERSION_ESQUEMA_SOPORTADA &&
    typeof candidato.generado_en === 'string' &&
    Array.isArray(candidato.productos)
  );
}

export function esProductoPublicado(datos: unknown): datos is ProductoPublicado {
  if (typeof datos !== 'object' || datos === null) return false;
  const candidato = datos as Record<string, unknown>;
  return (
    typeof candidato.id === 'string' &&
    typeof candidato.ruta === 'string' &&
    typeof candidato.actualizado_en === 'string' &&
    !Number.isNaN(new Date(candidato.actualizado_en).getTime()) &&
    typeof candidato.vigencia_min === 'number'
  );
}

/**
 * Lee el manifiesto, busca el producto `id` y descarga su contenido.
 * Nunca rellena: si algo falta, lo dice.
 */
export async function consultarProducto<T>(
  id: string,
  validar: Validador<T>,
  { raiz = RAIZ_DATOS, buscar = fetch }: { raiz?: string; buscar?: typeof fetch } = {},
): Promise<Resultado<T>> {
  try {
    const manifiesto = await leerJson(`${raiz}manifiesto.json`, buscar);
    if (manifiesto.tipo !== 'json')
      return { tipo: manifiesto.tipo === 'no-existe' ? 'sin-datos' : 'sin-conexion' };
    if (!esManifiesto(manifiesto.datos)) return { tipo: 'error' };

    const producto = manifiesto.datos.productos.find((candidato) => candidato.id === id);
    if (!producto) return { tipo: 'sin-datos' };
    if (!esProductoPublicado(producto)) return { tipo: 'error' };

    const contenido = await leerJson(`${raiz}${producto.ruta}`, buscar);
    if (contenido.tipo === 'sin-conexion') return contenido;
    // El manifiesto lo anuncia pero no está: es un fallo de publicación, no "aún no hay datos".
    if (contenido.tipo === 'no-existe' || !validar(contenido.datos)) return { tipo: 'error' };

    return { tipo: 'listo', copia: { producto, datos: contenido.datos } };
  } catch {
    return { tipo: 'error' };
  }
}
