import type { Manifiesto } from '@radar/contratos';

const VERSION_ESQUEMA_SOPORTADA = 1;

export const URL_MANIFIESTO = `${import.meta.env.BASE_URL}datos/manifiesto.json`;

/**
 * Lee el manifiesto publicado por el pipeline.
 * Devuelve `null` si todavía no se ha publicado ninguno (404).
 */
export async function leerManifiesto(url: string = URL_MANIFIESTO): Promise<Manifiesto | null> {
  const respuesta = await fetch(url, { cache: 'no-cache' });
  if (respuesta.status === 404) return null;
  if (!respuesta.ok) throw new Error(`El manifiesto respondió ${respuesta.status}`);

  // Sin datos publicados, un servidor estático puede devolver la página HTML en vez de un 404.
  if (!respuesta.headers.get('content-type')?.includes('json')) return null;

  const datos: unknown = await respuesta.json();
  if (!esManifiesto(datos)) throw new Error('El manifiesto tiene un formato no soportado');
  return datos;
}

function esManifiesto(datos: unknown): datos is Manifiesto {
  if (typeof datos !== 'object' || datos === null) return false;
  const candidato = datos as Record<string, unknown>;
  return (
    candidato.version_esquema === VERSION_ESQUEMA_SOPORTADA &&
    typeof candidato.generado_en === 'string' &&
    Array.isArray(candidato.productos)
  );
}
