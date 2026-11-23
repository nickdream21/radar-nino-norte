import { describe, expect, it } from 'vitest';
import {
  describirAntiguedad,
  describirAntiguedadCompleta,
  describirDiaCorto,
  describirMomento,
  describirMomentoConDe,
  formatearFecha,
  formatearHoraLima,
  formatearMes,
  superoMinutos,
} from './hora';

const AHORA = new Date('2026-11-23T14:39:00Z'); // 9:39 a. m. del 23 en Lima
const haceMinutos = (minutos: number) => new Date(AHORA.getTime() - minutos * 60_000);

describe('formatearHoraLima', () => {
  it.each([
    ['2026-11-23T13:50:00Z', '8:50 a. m.'],
    ['2026-11-23T05:05:00Z', '12:05 a. m.'],
    ['2026-11-23T17:00:00Z', '12:00 p. m.'],
    ['2026-11-23T18:05:00Z', '1:05 p. m.'],
    ['2026-11-24T04:59:00Z', '11:59 p. m.'],
  ])('%s se muestra como %s', (utc, esperado) => {
    expect(formatearHoraLima(new Date(utc))).toBe(esperado);
  });
});

describe('describirDiaCorto', () => {
  it('no menciona el día si es hoy en Lima', () => {
    expect(describirDiaCorto(new Date('2026-11-23T05:00:00Z'), AHORA)).toBeNull();
  });

  it('usa el día de Lima, no el UTC: 04:00 UTC del 23 es ayer', () => {
    expect(describirDiaCorto(new Date('2026-11-23T04:00:00Z'), AHORA)).toBe('ayer');
  });

  it('da la fecha si es de antes de ayer', () => {
    expect(describirDiaCorto(new Date('2026-11-21T15:00:00Z'), AHORA)).toBe('21 nov');
  });
});

describe('formatearFecha', () => {
  it('da el día de Lima sin año si es el año en curso', () => {
    expect(formatearFecha(new Date('2026-11-13T05:00:00Z'), AHORA)).toBe('13 de noviembre');
  });

  it('las 00:00 UTC son el día anterior en Lima', () => {
    expect(formatearFecha(new Date('2026-11-18T00:00:00Z'), AHORA)).toBe('17 de noviembre');
  });

  it('con zona UTC lee el día de calendario de la fuente', () => {
    expect(formatearFecha(new Date('2026-11-18T00:00:00Z'), AHORA, 'utc')).toBe('18 de noviembre');
  });

  it('añade el año si no es el actual', () => {
    expect(formatearFecha(new Date('2025-12-30T17:00:00Z'), AHORA)).toBe('30 de diciembre de 2025');
  });
});

describe('formatearMes', () => {
  it('nombra el mes y el año', () => {
    expect(formatearMes(2026, 9)).toBe('septiembre de 2026');
  });
});

describe('describirMomento', () => {
  it.each([
    ['2026-11-23T11:10:00Z', 'hoy a las 6:10 a. m.', 'de hoy a las 6:10 a. m.'],
    ['2026-11-22T23:10:00Z', 'ayer a las 6:10 p. m.', 'de ayer a las 6:10 p. m.'],
    ['2026-11-22T18:05:00Z', 'ayer a la 1:05 p. m.', 'de ayer a la 1:05 p. m.'],
    [
      '2026-11-20T20:00:00Z',
      'el 20 de noviembre a las 3:00 p. m.',
      'del 20 de noviembre a las 3:00 p. m.',
    ],
  ])('%s → "%s"', (utc, momento, conDe) => {
    expect(describirMomento(new Date(utc), AHORA)).toBe(momento);
    expect(describirMomentoConDe(new Date(utc), AHORA)).toBe(conDe);
  });

  it('con el reloj del teléfono atrasado, una fecha futura se da completa, no como "hoy"', () => {
    expect(describirMomento(new Date('2026-11-23T16:00:00Z'), AHORA)).toBe(
      'el 23 de noviembre a las 11:00 a. m.',
    );
  });
});

describe('describirAntiguedad', () => {
  it.each([
    [0, 'hace un momento'],
    [1, 'hace 1 min'],
    [59, 'hace 59 min'],
    [60, 'hace 1 h'],
    [23 * 60 + 59, 'hace 23 h'],
    [24 * 60, 'hace 1 día'],
    [3 * 24 * 60, 'hace 3 días'],
  ])('a los %i minutos dice "%s"', (minutos, esperado) => {
    expect(describirAntiguedad(haceMinutos(minutos), AHORA)).toBe(esperado);
  });

  it('tolera un desfase de segundos entre relojes', () => {
    expect(describirAntiguedad(new Date(AHORA.getTime() + 30_000), AHORA)).toBe('hace un momento');
  });

  it('no finge que una fecha futura es reciente', () => {
    expect(describirAntiguedad(haceMinutos(-5), AHORA)).toBeNull();
  });
});

describe('describirAntiguedadCompleta', () => {
  it('solo la relativa hasta una hora', () => {
    expect(describirAntiguedadCompleta(haceMinutos(15), AHORA)).toBe('hace 15 min');
    expect(describirAntiguedadCompleta(haceMinutos(60), AHORA)).toBe('hace 1 h');
  });

  it('relativa y absoluta pasada una hora', () => {
    expect(describirAntiguedadCompleta(haceMinutos(3 * 60 + 29), AHORA)).toBe(
      'hace 3 h, hoy a las 6:10 a. m.',
    );
  });

  it('solo la absoluta si la fecha está en el futuro', () => {
    expect(describirAntiguedadCompleta(haceMinutos(-120), AHORA)).toBe(
      'el 23 de noviembre a las 11:39 a. m.',
    );
  });
});

describe('superoMinutos', () => {
  it('no mientras no pase el umbral, sí en cuanto lo supera', () => {
    expect(superoMinutos(haceMinutos(120), AHORA, 120)).toBe(false);
    expect(superoMinutos(haceMinutos(121), AHORA, 120)).toBe(true);
  });

  it('una fecha futura nunca superó el umbral', () => {
    expect(superoMinutos(haceMinutos(-500), AHORA, 1)).toBe(false);
  });
});
