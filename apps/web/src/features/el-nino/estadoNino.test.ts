import { describe, expect, it } from 'vitest';
import { comunicadoEsAntiguo, esEstadoNino } from './estadoNino';
import grabado from './respuestas/estado-nino-2026-11-23.json?raw';
import { partesCifraMar, textoIcen, textoNino12 } from './textos';

const ESTADO = JSON.parse(grabado) as Record<string, unknown>;

describe('esEstadoNino', () => {
  it('acepta el producto publicado', () => {
    expect(esEstadoNino(ESTADO)).toBe(true);
  });

  it('acepta bloques null', () => {
    expect(
      esEstadoNino({
        ...ESTADO,
        indices_semanales: null,
        icen: null,
        mar_paita: null,
        enfen: null,
      }),
    ).toBe(true);
  });

  it('rechaza otra versión del esquema', () => {
    expect(esEstadoNino({ ...ESTADO, version_esquema: 2 })).toBe(false);
  });

  it('rechaza un bloque al que le falta un campo que la pantalla usa', () => {
    expect(esEstadoNino({ ...ESTADO, mar_paita: { fecha_dato: '2026-11-21T12:00:00Z' } })).toBe(
      false,
    );
    expect(esEstadoNino({ ...ESTADO, enfen: { fecha_dato: 'no es fecha', comunicado: {} } })).toBe(
      false,
    );
  });
});

describe('comunicadoEsAntiguo', () => {
  const comunicado = new Date('2026-11-13T05:00:00Z');

  it('no antes de 21 días', () => {
    expect(comunicadoEsAntiguo(comunicado, new Date('2026-12-04T05:00:00Z'))).toBe(false);
  });

  it('sí pasados 21 días', () => {
    expect(comunicadoEsAntiguo(comunicado, new Date('2026-12-04T05:01:00Z'))).toBe(true);
  });
});

describe('textos con cifras', () => {
  it('mar más caliente o más frío que lo normal, con signo', () => {
    expect(partesCifraMar(2.4)).toEqual({
      cifra: '+2,4 °C',
      comparacion: 'más caliente que lo normal',
    });
    expect(partesCifraMar(-1.2)).toEqual({
      cifra: '−1,2 °C',
      comparacion: 'más frío que lo normal',
    });
  });

  it('en cero no afirma ni "más caliente" ni "más frío"', () => {
    expect(partesCifraMar(0.01)).toEqual({ cifra: '0,0 °C', comparacion: null });
  });

  it('Niño 1+2 da la anomalía y la temperatura real', () => {
    expect(textoNino12(5.7, 27.5, '18 de noviembre')).toBe(
      '+5,7 °C sobre lo normal; el mar está a 27,5 °C. Es una zona grande de mar frente a Ecuador y el norte del Perú. Semana del 18 de noviembre. Fuente: NOAA.',
    );
  });

  it('ICEN sin categoría', () => {
    const texto = textoIcen(1.2, 'septiembre de 2026');
    expect(texto).toMatch(/^\+1,2 °C\. /);
    expect(texto).not.toMatch(/débil|moderad|fuerte|extraordinari/i);
  });
});
