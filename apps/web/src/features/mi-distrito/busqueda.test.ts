import { describe, expect, it } from 'vitest';
import { buscar, normalizar, prepararIndice } from './busqueda';
import { CATALOGO } from './catalogo';
import { textoResultado } from './textos';

const indice = prepararIndice(CATALOGO.distritos);
const nombres = (texto: string) => buscar(indice, texto).map(textoResultado);

describe('normalizar', () => {
  it.each([
    ['Cañaris', 'canaris'],
    ['  CAÑARIS ', 'canaris'],
    ['Veintiséis   de Octubre', 'veintiseis de octubre'],
    ['Santa Cruz de Toled', 'santa cruz de toled'],
    ['San José-del Alto', 'san jose del alto'],
    ['ÁÉÍÓÚÜ áéíóúü', 'aeiouu aeiouu'],
    ['   ', ''],
  ])('"%s" → "%s"', (texto, esperado) => {
    expect(normalizar(texto)).toBe(esperado);
  });
});

describe('buscar', () => {
  it.each(['canaris', 'CAÑARIS', '  cañaris ', 'Canaris'])('"%s" encuentra Cañaris', (texto) => {
    expect(nombres(texto)).toEqual(['Cañaris — Ferreñafe, Lambayeque']);
  });

  it('"piura" da primero el distrito homónimo y luego los de la provincia en orden alfabético', () => {
    expect(nombres('piura')).toEqual([
      'Piura — Piura, Piura',
      'Castilla — Piura, Piura',
      'Catacaos — Piura, Piura',
      'Cura Mori — Piura, Piura',
      'El Tallán — Piura, Piura',
      'La Arena — Piura, Piura',
      'La Unión — Piura, Piura',
      'Las Lomas — Piura, Piura',
      'Tambo Grande — Piura, Piura',
      'Veintiséis de Octubre — Piura, Piura',
    ]);
  });

  it('distingue los nombres repetidos por su provincia y departamento', () => {
    expect(nombres('santa rosa')).toEqual([
      'Santa Rosa — Chiclayo, Lambayeque',
      'Santa Rosa — Jaén, Cajamarca',
    ]);
  });

  it('coincide con el inicio de cualquier palabra del nombre, no con el medio', () => {
    expect(nombres('octubre')).toEqual(['Veintiséis de Octubre — Piura, Piura']);
    expect(nombres('ctubre')).toEqual([]);
  });

  it('coincide con palabras de la provincia', () => {
    const resultado = buscar(indice, 'carrion');
    expect(resultado.length).toBeGreaterThan(0);
    expect(resultado.every((d) => d.provincia === 'Sánchez Carrión')).toBe(true);
  });

  it('el nombre que empieza por lo escrito va antes que la palabra interior', () => {
    const resultado = nombres('san jose');
    expect(resultado[0]).toMatch(/^San José — /);
    expect(resultado.every((t) => /San José/.test(t))).toBe(true);
  });

  it('sin texto o sin coincidencias no devuelve nada', () => {
    expect(buscar(indice, '')).toEqual([]);
    expect(buscar(indice, '   ')).toEqual([]);
    expect(buscar(indice, 'Lima')).toEqual([]);
  });

  it('solo normaliza lo escrito: la lista se normaliza una vez al preparar el índice', () => {
    const entrada = indice.entradas.find((e) => e.distrito.nombre === 'Cañaris');
    expect(entrada?.nombre).toBe('canaris');
  });
});
