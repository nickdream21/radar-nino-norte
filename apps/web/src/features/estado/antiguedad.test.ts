import { describe, expect, it } from 'vitest';
import { describirAntiguedad } from './antiguedad';

const AHORA = new Date('2026-11-23T12:00:00Z');
const haceMinutos = (minutos: number) => new Date(AHORA.getTime() - minutos * 60_000);

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

  it('trata una fecha futura (reloj desajustado) como reciente', () => {
    expect(describirAntiguedad(haceMinutos(-5), AHORA)).toBe('hace un momento');
  });
});
