import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { BarraNavegacion } from './BarraNavegacion';
import { BarraSuperior } from './BarraSuperior';
import { navegar, prepararHistorial, seccionDesdeFragmento } from './secciones';

describe('seccionDesdeFragmento', () => {
  it.each([
    ['', 'mi-distrito'],
    ['#/', 'mi-distrito'],
    ['#/mapa', 'mapa'],
    ['#/el-nino', 'el-nino'],
    ['#/acerca', 'acerca'],
    ['#mapa', 'mapa'],
    ['#inicio', 'mi-distrito'],
    ['#/desconocida', 'mi-distrito'],
    ['#/toString', 'mi-distrito'],
  ])('"%s" lleva a %s', (fragmento, esperada) => {
    expect(seccionDesdeFragmento(fragmento)).toBe(esperada);
  });
});

describe('BarraNavegacion', () => {
  it('tiene las tres secciones y marca la activa sin depender solo del color', () => {
    render(<BarraNavegacion activa="el-nino" />);

    const barra = within(screen.getByRole('navigation', { name: 'Secciones' }));
    expect(barra.getAllByRole('link').map((enlace) => enlace.textContent)).toEqual([
      'Mi distrito',
      'Mapa',
      'El Niño',
    ]);
    const activa = barra.getByRole('link', { name: 'El Niño' });
    expect(activa).toHaveAttribute('aria-current', 'page');
    expect(activa).toHaveAttribute('href', '#/el-nino');
    expect(activa).toHaveClass('font-bold', 'bg-white');
    expect(barra.getByRole('link', { name: 'Mapa' })).not.toHaveAttribute('aria-current');
    expect(barra.getByRole('link', { name: 'Mapa' })).not.toHaveClass('font-bold');
  });
});

describe('BarraSuperior', () => {
  it('enlaza a los avisos de SENAMHI avisando que abre otra página', () => {
    render(<BarraSuperior />);
    const enlace = screen.getByRole('link', {
      name: /^Avisos SENAMHI\s*\(se abre en otra página\)$/,
    });
    expect(enlace).toHaveAttribute('href', 'https://www.senamhi.gob.pe/?p=aviso-meteorologico');
    expect(enlace).toHaveAttribute('target', '_blank');
  });
});

describe('historial', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('desde cualquier sección, Atrás vuelve a Mi distrito', async () => {
    prepararHistorial();
    const largo = window.history.length;

    navegar('mapa');
    expect(window.location.hash).toBe('#/mapa');
    navegar('el-nino');
    navegar('acerca');
    expect(window.location.hash).toBe('#/acerca');
    // Solo una entrada encima de Mi distrito, pase por las secciones que pase.
    expect(window.history.length).toBe(largo + 1);

    window.history.back();
    await waitFor(() => expect(window.location.hash).toBe('#/'));
  });

  it('al abrir directamente en una sección, pone Mi distrito debajo', async () => {
    window.history.replaceState(null, '', '/#/el-nino');
    prepararHistorial();
    expect(window.location.hash).toBe('#/el-nino');

    window.history.back();
    await waitFor(() => expect(window.location.hash).toBe('#/'));
  });
});

describe('App', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
    prepararHistorial();
    // Las pantallas con datos no deben salir a la red en las pruebas.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('sin red en pruebas'))),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('cada sección está a un toque, tiene un h1 y recibe el foco al llegar', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: 'Mi distrito' })).toBeInTheDocument();
    expect(screen.queryByText(/producto\(s\) disponibles/)).not.toBeInTheDocument();

    const barra = within(screen.getByRole('navigation', { name: 'Secciones' }));
    fireEvent.click(barra.getByRole('link', { name: 'El Niño' }));
    const titulo = await screen.findByRole('heading', { level: 1, name: 'El Niño' });
    expect(titulo).toHaveFocus();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);

    fireEvent.click(screen.getByRole('link', { name: 'Acerca de y fuentes' }));
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Acerca de y fuentes' }),
    ).toHaveFocus();
    expect(
      screen.getByText(/Esta app es un proyecto gratuito e independiente/),
    ).toBeInTheDocument();
    // La barra superior sigue en todas las secciones.
    expect(screen.getByRole('link', { name: /Avisos SENAMHI/ })).toBeInTheDocument();

    act(() => {
      fireEvent.click(barra.getByRole('link', { name: 'Mi distrito' }));
    });
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Mi distrito' }),
    ).toBeInTheDocument();
  });

  it('Mi distrito lo dice con honestidad y lleva a El Niño y al Mapa', () => {
    render(<App />);
    expect(
      screen.getByText(
        /Estamos preparando el pronóstico de lluvia por distrito\. Mientras tanto, mira los avisos de SENAMHI\./,
      ),
    ).toBeInTheDocument();
    const principal = within(screen.getByRole('main'));
    expect(principal.getByRole('link', { name: 'El Niño' })).toHaveAttribute('href', '#/el-nino');
    expect(principal.getByRole('link', { name: 'Mapa' })).toHaveAttribute('href', '#/mapa');
    expect(principal.getByRole('link', { name: /Ver avisos de SENAMHI/ })).toBeInTheDocument();
    expect(principal.getByRole('link', { name: 'Acerca de y fuentes' })).toBeInTheDocument();
  });
});
