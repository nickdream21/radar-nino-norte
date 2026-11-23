import { describe, expect, it } from 'vitest';
import { CATALOGO, type DistritoLista } from './catalogo';
import { DISTANCIA_MAXIMA_KM, distanciaKm, distritoMasCercano } from './geo';

const distrito = (ubigeo: string, latitud: number, longitud: number): DistritoLista => ({
  ubigeo,
  nombre: ubigeo,
  provincia: 'P',
  departamento: 'D',
  capital: { latitud, longitud },
});

describe('distanciaKm', () => {
  it('es cero en el mismo punto', () => {
    expect(
      distanciaKm({ latitud: -5.2, longitud: -80.6 }, { latitud: -5.2, longitud: -80.6 }),
    ).toBe(0);
  });

  it('un grado de latitud mide unos 111 km', () => {
    expect(distanciaKm({ latitud: -5, longitud: -80 }, { latitud: -6, longitud: -80 })).toBeCloseTo(
      111.2,
      0,
    );
  });

  it('Piura–Chiclayo mide unos 200 km en línea recta', () => {
    const piura = CATALOGO.porUbigeo('200101');
    const chiclayo = CATALOGO.porUbigeo('140101');
    if (!piura || !chiclayo) throw new Error('faltan capitales en el catálogo');
    expect(distanciaKm(piura.capital, chiclayo.capital)).toBeGreaterThan(195);
    expect(distanciaKm(piura.capital, chiclayo.capital)).toBeLessThan(205);
  });
});

describe('distritoMasCercano', () => {
  const lista = [distrito('a', -5, -80), distrito('b', -6, -80), distrito('c', -5.3, -80)];

  it('elige la capital más cercana', () => {
    const cercania = distritoMasCercano(lista, { latitud: -5.2, longitud: -80 });
    expect(cercania).toMatchObject({ tipo: 'dentro', distrito: { ubigeo: 'c' } });
  });

  it(`a más de ${DISTANCIA_MAXIMA_KM} km de toda capital está fuera de la zona`, () => {
    // 0,6° de latitud ≈ 67 km de la capital "b".
    expect(distritoMasCercano(lista, { latitud: -6.6, longitud: -80 })).toEqual({ tipo: 'fuera' });
    // 0,5° ≈ 56 km: todavía dentro.
    expect(distritoMasCercano(lista, { latitud: -6.5, longitud: -80 })).toMatchObject({
      tipo: 'dentro',
      distrito: { ubigeo: 'b' },
    });
  });

  it('con la lista vacía está fuera', () => {
    expect(distritoMasCercano([], { latitud: -5, longitud: -80 })).toEqual({ tipo: 'fuera' });
  });

  it('con el catálogo real: junto a la capital de Piura propone Piura; en Lima, fuera', () => {
    expect(
      distritoMasCercano(CATALOGO.distritos, { latitud: -5.153, longitud: -80.657 }),
    ).toMatchObject({ tipo: 'dentro', distrito: { nombre: 'Piura', provincia: 'Piura' } });
    expect(distritoMasCercano(CATALOGO.distritos, { latitud: -12.046, longitud: -77.043 })).toEqual(
      { tipo: 'fuera' },
    );
  });
});
