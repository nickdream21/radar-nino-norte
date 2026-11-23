import { describe, expect, it } from 'vitest';
import imerg from './respuestas/gibs-dominios-imerg-2026-11-23.xml?raw';
import infrarrojo from './respuestas/gibs-dominios-infrarrojo-2026-11-23.xml?raw';
import nowcoast from './respuestas/nowcoast-capacidades-2026-11-23.xml?raw';
import {
  describirDiaPeru,
  esAntigua,
  formatearHoraPeru,
  ultimoInstante,
  ultimoTiempoGibs,
  ultimoTiempoWms,
} from './tiempo';

describe('ultimoInstante', () => {
  it('toma el fin del último intervalo', () => {
    expect(
      ultimoInstante(
        '2026-11-21/2026-11-21T03:30:00Z/PT10M,2026-11-22T19:50:00Z/2026-11-23T13:50:00Z/PT10M',
      ),
    ).toEqual(new Date('2026-11-23T13:50:00Z'));
  });

  it('toma el mayor de una lista de instantes, aunque no estén en orden', () => {
    expect(
      ultimoInstante('2026-11-23T14:15:00.000Z, 2026-11-23T08:15:00.000Z,2026-11-23T14:00:00.000Z'),
    ).toEqual(new Date('2026-11-23T14:15:00Z'));
  });

  it('devuelve null si no hay ningún tiempo válido', () => {
    expect(ultimoInstante('')).toBeNull();
    expect(ultimoInstante('no es una fecha')).toBeNull();
  });
});

describe('respuestas grabadas de los servicios', () => {
  it('GIBS infrarrojo: última imagen 13:50 UTC', () => {
    expect(ultimoTiempoGibs(infrarrojo)).toEqual(new Date('2026-11-23T13:50:00Z'));
  });

  it('GIBS IMERG: última imagen 09:30 UTC', () => {
    expect(ultimoTiempoGibs(imerg)).toEqual(new Date('2026-11-23T09:30:00Z'));
  });

  it('nowCOAST: última imagen de rayos 14:15 UTC', () => {
    expect(ultimoTiempoWms(nowcoast, 'ldn_lightning_strike_density')).toEqual(
      new Date('2026-11-23T14:15:00Z'),
    );
  });

  it('nowCOAST: null si la capa no existe', () => {
    expect(ultimoTiempoWms(nowcoast, 'capa_inexistente')).toBeNull();
  });

  it('null ante una respuesta que no es XML válido', () => {
    expect(ultimoTiempoGibs('<html><body>Error')).toBeNull();
    expect(ultimoTiempoWms('Service unavailable', 'ldn_lightning_strike_density')).toBeNull();
  });

  it('null si GIBS no informa ningún tiempo', () => {
    expect(ultimoTiempoGibs('<Domains><DimensionDomain></DimensionDomain></Domains>')).toBeNull();
  });
});

describe('hora de Perú (UTC−5)', () => {
  it.each([
    ['2026-11-23T13:50:00Z', '8:50 a. m.'],
    ['2026-11-23T05:05:00Z', '12:05 a. m.'],
    ['2026-11-23T17:00:00Z', '12:00 p. m.'],
    ['2026-11-23T18:05:00Z', '1:05 p. m.'],
    ['2026-11-24T04:59:00Z', '11:59 p. m.'],
  ])('%s se muestra como %s', (utc, esperado) => {
    expect(formatearHoraPeru(new Date(utc))).toBe(esperado);
  });

  const ahora = new Date('2026-11-23T14:39:00Z'); // 9:39 a. m. del 23 en Perú

  it('no menciona el día si es hoy en Perú', () => {
    expect(describirDiaPeru(new Date('2026-11-23T05:00:00Z'), ahora)).toBeNull();
  });

  it('usa el día de Perú, no el UTC: 04:00 UTC del 23 es ayer', () => {
    expect(describirDiaPeru(new Date('2026-11-23T04:00:00Z'), ahora)).toBe('ayer');
  });

  it('da la fecha si es de antes de ayer', () => {
    expect(describirDiaPeru(new Date('2026-11-21T15:00:00Z'), ahora)).toBe('21 nov');
  });
});

describe('esAntigua', () => {
  const ahora = new Date('2026-11-23T14:00:00Z');

  it('no lo es mientras no pase el umbral', () => {
    expect(esAntigua(new Date('2026-11-23T12:00:00Z'), ahora, 120)).toBe(false);
  });

  it('lo es en cuanto lo supera', () => {
    expect(esAntigua(new Date('2026-11-23T11:59:00Z'), ahora, 120)).toBe(true);
  });
});
