import { describe, expect, it } from 'vitest';
import {
  admiteReintento,
  calcularVista,
  esAntiguo,
  estadoInicial,
  reducir,
  type EstadoProducto,
} from './estadoProducto';
import type { Copia } from './manifiesto';
import { textoFranja } from './textos';

const AHORA = new Date('2026-11-23T14:39:00Z'); // 9:39 a. m. en Lima

function copia(actualizadoEn: string, vigenciaMin = 60): Copia<string> {
  return {
    producto: {
      id: 'prueba',
      ruta: 'prueba.json',
      fuente: 'Prueba',
      actualizado_en: actualizadoEn,
      vigencia_min: vigenciaMin,
    },
    datos: 'contenido',
  };
}

const RECIENTE = copia('2026-11-23T14:00:00Z');
const VIEJA = copia('2026-11-22T23:10:00Z'); // ayer 6:10 p. m.

const textos = (estado: EstadoProducto<string>) =>
  calcularVista(estado, AHORA).franjas.map((franja) => textoFranja(franja, AHORA));

describe('esAntiguo', () => {
  it('usa la vigencia que declara el producto', () => {
    expect(esAntiguo(copia('2026-11-23T13:39:00Z', 60), AHORA)).toBe(false);
    expect(esAntiguo(copia('2026-11-23T13:38:00Z', 60), AHORA)).toBe(true);
    expect(esAntiguo(copia('2026-11-21T12:00:00Z', 5760), AHORA)).toBe(false);
  });

  it('con el reloj atrasado, un dato "del futuro" no se marca como antiguo', () => {
    expect(esAntiguo(copia('2026-11-23T20:00:00Z', 60), AHORA)).toBe(false);
  });
});

describe('calcularVista', () => {
  it('cargando sin nada guardado: solo "Buscando los datos…", sin contenido', () => {
    const vista = calcularVista(estadoInicial<string>(null, true), AHORA);
    expect(vista.copia).toBeNull();
    expect(textos(estadoInicial(null, true))).toEqual(['Buscando los datos…']);
  });

  it('cargando con dato guardado: lo muestra de inmediato con su hora', () => {
    const vista = calcularVista(estadoInicial(RECIENTE, true), AHORA);
    expect(vista.copia).toBe(RECIENTE);
    expect(vista.momento).toEqual(new Date('2026-11-23T14:00:00Z'));
  });

  it('carga lenta: ofrece reintentar', () => {
    const vista = calcularVista<string>({ copia: null, consulta: 'lenta' }, AHORA);
    expect(textos({ copia: null, consulta: 'lenta' })).toEqual([
      'Está tardando. Puede ser tu señal.',
    ]);
    expect(vista.franjas.every(admiteReintento)).toBe(true);
  });

  it('sin datos todavía: nunca un valor por defecto', () => {
    const vista = calcularVista<string>({ copia: null, consulta: 'sin-datos' }, AHORA);
    expect(vista.copia).toBeNull();
    expect(textos({ copia: null, consulta: 'sin-datos' })).toEqual([
      'Aún no tenemos estos datos. Estamos preparándolos.',
    ]);
  });

  it('listo y vigente: sin franjas', () => {
    expect(calcularVista({ copia: RECIENTE, consulta: 'listo' }, AHORA).franjas).toEqual([]);
  });

  it('listo pero vencido: franja de dato antiguo con la hora', () => {
    expect(textos({ copia: VIEJA, consulta: 'listo' })).toEqual([
      'Dato de ayer a las 6:10 p. m. Puede haber cambiado.',
    ]);
  });

  it('sin conexión con dato guardado: lo dice y muestra el dato', () => {
    const estado: EstadoProducto<string> = { copia: RECIENTE, consulta: 'sin-conexion' };
    expect(calcularVista(estado, AHORA).copia).toBe(RECIENTE);
    expect(textos(estado)).toEqual([
      'Sin conexión. Te mostramos lo último guardado: hoy a las 9:00 a. m.',
    ]);
  });

  it('sin conexión sin dato guardado: texto propio y reintentar', () => {
    const estado: EstadoProducto<string> = { copia: null, consulta: 'sin-conexion' };
    expect(textos(estado)).toEqual([
      'Sin conexión y todavía no hay datos guardados en este celular. Conéctate una vez para descargarlos.',
    ]);
    expect(calcularVista(estado, AHORA).franjas.every(admiteReintento)).toBe(true);
  });

  it('sin conexión con un dato vencido: ambas franjas, primero la de conexión', () => {
    expect(textos({ copia: VIEJA, consulta: 'sin-conexion' })).toEqual([
      'Sin conexión. Te mostramos lo último guardado: ayer a las 6:10 p. m.',
      'Dato de ayer a las 6:10 p. m. Puede haber cambiado.',
    ]);
  });

  it('error: texto distinto del de sin conexión, con reintentar', () => {
    const estado: EstadoProducto<string> = { copia: null, consulta: 'error' };
    expect(textos(estado)).toEqual([
      'No pudimos cargar los datos. No es tu culpa: inténtalo de nuevo en unos minutos.',
    ]);
    expect(calcularVista(estado, AHORA).franjas.every(admiteReintento)).toBe(true);
  });
});

describe('reducir', () => {
  it('un fallo no borra el último dato válido', () => {
    const estado = reducir<string>(
      { copia: RECIENTE, consulta: 'cargando' },
      { tipo: 'resultado', resultado: { tipo: 'error' } },
    );
    expect(estado).toEqual({ copia: RECIENTE, consulta: 'error' });
  });

  it('un resultado nuevo reemplaza la copia', () => {
    const estado = reducir<string>(
      { copia: VIEJA, consulta: 'cargando' },
      { tipo: 'resultado', resultado: { tipo: 'listo', copia: RECIENTE } },
    );
    expect(estado).toEqual({ copia: RECIENTE, consulta: 'listo' });
  });

  it('"lenta" solo aplica mientras se sigue cargando', () => {
    expect(reducir<string>({ copia: null, consulta: 'listo' }, { tipo: 'lenta' }).consulta).toBe(
      'listo',
    );
    expect(reducir<string>({ copia: null, consulta: 'cargando' }, { tipo: 'lenta' }).consulta).toBe(
      'lenta',
    );
  });

  it('empieza sin conexión si el teléfono no tiene red', () => {
    expect(estadoInicial(null, false).consulta).toBe('sin-conexion');
  });
});
