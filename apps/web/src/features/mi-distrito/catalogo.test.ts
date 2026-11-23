import { describe, expect, it } from 'vitest';
import { CATALOGO } from './catalogo';

describe('CATALOGO', () => {
  it('tiene los 327 distritos con ubigeo único', () => {
    expect(CATALOGO.distritos).toHaveLength(327);
    expect(new Set(CATALOGO.distritos.map((d) => d.ubigeo)).size).toBe(327);
  });

  it('busca por ubigeo y no encuentra los que no existen', () => {
    expect(CATALOGO.porUbigeo('140202')).toMatchObject({
      nombre: 'Cañaris',
      provincia: 'Ferreñafe',
      departamento: 'Lambayeque',
    });
    expect(CATALOGO.porUbigeo('150101')).toBeUndefined();
  });

  it('ordena departamentos, provincias y distritos en orden alfabético español', () => {
    expect(CATALOGO.departamentos()).toEqual([
      'Cajamarca',
      'La Libertad',
      'Lambayeque',
      'Piura',
      'Tumbes',
    ]);
    expect(CATALOGO.provincias('Lambayeque')).toEqual(['Chiclayo', 'Ferreñafe', 'Lambayeque']);
    const distritos = CATALOGO.distritosDe('Lambayeque', 'Ferreñafe').map((d) => d.nombre);
    expect(distritos).toEqual([...distritos].sort((a, b) => a.localeCompare(b, 'es')));
    expect(distritos).toContain('Cañaris');
  });

  it('cada provincia pertenece a un solo departamento en la lista de tres pasos', () => {
    const total = CATALOGO.departamentos()
      .flatMap((dep) => CATALOGO.provincias(dep).map((prov) => CATALOGO.distritosDe(dep, prov)))
      .reduce((suma, lista) => suma + lista.length, 0);
    expect(total).toBe(327);
  });
});
