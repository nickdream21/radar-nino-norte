import { describe, expect, it } from 'vitest';
import { formatearAnomalia, formatearDecimal, signoAnomalia } from './numeros';

describe('formatearDecimal', () => {
  it.each([
    [27.5, '27,5'],
    [30, '30,0'],
    [27.46, '27,5'],
    [-1.24, '−1,2'],
    [-0.04, '0,0'],
  ])('%d → %s', (valor, esperado) => {
    expect(formatearDecimal(valor)).toBe(esperado);
  });
});

describe('formatearAnomalia', () => {
  it.each([
    [2.4, '+2,4 °C'],
    [8.9, '+8,9 °C'],
    [-0.8, '−0,8 °C'],
    [0, '0,0 °C'],
    [0.04, '0,0 °C'],
    [-0.04, '0,0 °C'],
  ])('%d → %s', (valor, esperado) => {
    expect(formatearAnomalia(valor)).toBe(esperado);
  });
});

describe('signoAnomalia', () => {
  it('decide el signo después de redondear, igual que la cifra mostrada', () => {
    expect(signoAnomalia(0.06)).toBe('positiva');
    expect(signoAnomalia(0.04)).toBe('cero');
    expect(signoAnomalia(-0.06)).toBe('negativa');
  });
});
