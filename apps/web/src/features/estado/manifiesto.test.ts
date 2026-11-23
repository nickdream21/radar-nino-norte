import type { Manifiesto } from '@radar/contratos';
import { describe, expect, it } from 'vitest';
import { consultarProducto } from './manifiesto';

const MANIFIESTO: Manifiesto = {
  version_esquema: 1,
  generado_en: '2026-11-23T14:53:16Z',
  version_pipeline: '0.1.0',
  productos: [
    {
      id: 'prueba',
      ruta: 'prueba/datos.json',
      fuente: 'Prueba',
      actualizado_en: '2026-11-21T12:00:00Z',
      vigencia_min: 5760,
    },
  ],
};

const esTexto = (datos: unknown): datos is { texto: string } =>
  typeof datos === 'object' && datos !== null && 'texto' in datos;

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'content-type': 'application/json' },
  });

/** `fetch` falso que responde según la ruta pedida, sin red. */
function servidor(rutas: Record<string, () => Response | Promise<Response>>): typeof fetch {
  return (entrada) => {
    const url = String(entrada);
    const responder = rutas[url];
    return Promise.resolve(responder ? responder() : new Response('', { status: 404 }));
  };
}

const consultar = (buscar: typeof fetch) =>
  consultarProducto('prueba', esTexto, { raiz: '/datos/', buscar });

describe('consultarProducto', () => {
  it('devuelve el producto con su entrada del manifiesto', async () => {
    const resultado = await consultar(
      servidor({
        '/datos/manifiesto.json': () => json(MANIFIESTO),
        '/datos/prueba/datos.json': () => json({ texto: 'hola' }),
      }),
    );
    expect(resultado).toEqual({
      tipo: 'listo',
      copia: { producto: MANIFIESTO.productos[0], datos: { texto: 'hola' } },
    });
  });

  it('sin manifiesto publicado: sin datos', async () => {
    expect(await consultar(servidor({}))).toEqual({ tipo: 'sin-datos' });
  });

  it('un servidor estático que responde HTML en vez de 404: sin datos', async () => {
    const html = () => new Response('<html>', { headers: { 'content-type': 'text/html' } });
    expect(await consultar(servidor({ '/datos/manifiesto.json': html }))).toEqual({
      tipo: 'sin-datos',
    });
  });

  it('el manifiesto no anuncia el producto: sin datos', async () => {
    const vacio = { ...MANIFIESTO, productos: [] };
    expect(await consultar(servidor({ '/datos/manifiesto.json': () => json(vacio) }))).toEqual({
      tipo: 'sin-datos',
    });
  });

  it('la petición no llega a ninguna parte: sin conexión', async () => {
    const sinRed: typeof fetch = () => Promise.reject(new TypeError('Failed to fetch'));
    expect(await consultar(sinRed)).toEqual({ tipo: 'sin-conexion' });
  });

  it('el servidor falla: error, no "sin conexión"', async () => {
    expect(await consultar(servidor({ '/datos/manifiesto.json': () => json({}, 503) }))).toEqual({
      tipo: 'error',
    });
  });

  it('el manifiesto lo anuncia pero el archivo no está: error', async () => {
    expect(await consultar(servidor({ '/datos/manifiesto.json': () => json(MANIFIESTO) }))).toEqual(
      { tipo: 'error' },
    );
  });

  it('formato no soportado: error', async () => {
    const otraVersion = { ...MANIFIESTO, version_esquema: 2 };
    expect(
      await consultar(servidor({ '/datos/manifiesto.json': () => json(otraVersion) })),
    ).toEqual({ tipo: 'error' });
    expect(
      await consultar(
        servidor({
          '/datos/manifiesto.json': () => json(MANIFIESTO),
          '/datos/prueba/datos.json': () => json({ otra: 'cosa' }),
        }),
      ),
    ).toEqual({ tipo: 'error' });
  });

  it('JSON roto: error', async () => {
    const roto = () =>
      new Response('{"version', { headers: { 'content-type': 'application/json' } });
    expect(await consultar(servidor({ '/datos/manifiesto.json': roto }))).toEqual({
      tipo: 'error',
    });
  });
});
