import type { Manifiesto } from '@radar/contratos';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EstadoDatos } from './EstadoDatos';

const ahora = () => new Date('2026-11-23T12:00:00Z');

const MANIFIESTO: Manifiesto = {
  version_esquema: 1,
  generado_en: '2026-11-23T11:45:00Z',
  version_pipeline: '0.0.0',
  productos: [],
};

describe('EstadoDatos', () => {
  it('muestra la antigüedad cuando hay manifiesto', async () => {
    render(<EstadoDatos leer={() => Promise.resolve(MANIFIESTO)} ahora={ahora} />);

    expect(await screen.findByText(/Actualizado hace 15 min/)).toBeInTheDocument();
  });

  it('explica que aún no hay datos cuando no existe manifiesto', async () => {
    render(<EstadoDatos leer={() => Promise.resolve(null)} ahora={ahora} />);

    expect(await screen.findByText(/Aún no hay datos publicados/)).toBeInTheDocument();
  });

  it('avisa del fallo sin inventar un estado', async () => {
    render(<EstadoDatos leer={() => Promise.reject(new Error('sin red'))} ahora={ahora} />);

    expect(await screen.findByText(/No pudimos consultar los datos/)).toBeInTheDocument();
  });
});
