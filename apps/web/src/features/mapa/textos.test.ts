import { describe, expect, it } from 'vitest';
import { textoHoraImagen } from './textos';

const AHORA = new Date('2026-11-23T14:39:00Z'); // 9:39 a. m. en Perú

describe('textoHoraImagen', () => {
  it('da la hora de Perú y la antigüedad', () => {
    expect(textoHoraImagen(new Date('2026-11-23T13:50:00Z'), AHORA)).toBe(
      'Imagen de las 8:50 a. m. (hora de Perú), hace 49 min',
    );
  });

  it('usa "la" con la una', () => {
    expect(textoHoraImagen(new Date('2026-11-23T06:30:00Z'), AHORA)).toBe(
      'Imagen de la 1:30 a. m. (hora de Perú), hace 8 h',
    );
  });

  it('dice "ayer" si la imagen es del día anterior en Perú', () => {
    expect(textoHoraImagen(new Date('2026-11-23T03:00:00Z'), AHORA)).toBe(
      'Imagen de ayer a las 10:00 p. m. (hora de Perú), hace 11 h',
    );
  });

  it('da la fecha si es más vieja', () => {
    expect(textoHoraImagen(new Date('2026-11-20T20:00:00Z'), AHORA)).toBe(
      'Imagen del 20 nov a las 3:00 p. m. (hora de Perú), hace 2 días',
    );
  });

  it('con el reloj del teléfono atrasado no dice "hace un momento": solo la hora', () => {
    expect(textoHoraImagen(new Date('2026-11-23T16:00:00Z'), AHORA)).toBe(
      'Imagen de las 11:00 a. m. (hora de Perú)',
    );
  });
});
