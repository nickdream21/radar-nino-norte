import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BarraNavegacion } from './BarraNavegacion';
import { seccionDesdeFragmento } from './secciones';

describe('seccionDesdeFragmento', () => {
  it.each([
    ['', 'inicio'],
    ['#inicio', 'inicio'],
    ['#mapa', 'mapa'],
    ['#desconocida', 'inicio'],
  ])('"%s" lleva a %s', (fragmento, esperada) => {
    expect(seccionDesdeFragmento(fragmento)).toBe(esperada);
  });
});

describe('BarraNavegacion', () => {
  it('marca la sección activa sin depender solo del color', () => {
    render(<BarraNavegacion activa="mapa" />);

    const mapa = screen.getByRole('link', { name: 'Mapa' });
    expect(mapa).toHaveAttribute('aria-current', 'page');
    expect(mapa).toHaveAttribute('href', '#mapa');
    expect(mapa.querySelector('span')).toHaveClass('underline');
    expect(screen.getByRole('link', { name: 'Inicio' })).not.toHaveAttribute('aria-current');
  });
});
