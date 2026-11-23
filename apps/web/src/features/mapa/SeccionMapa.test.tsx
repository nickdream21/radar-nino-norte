import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { DefinicionCapa, IdCapa } from './capas';
import { SeccionMapa } from './SeccionMapa';
import type { PropsMapa } from './tipos';

const AHORA = new Date('2026-11-23T14:39:00Z'); // 9:39 a. m. en Perú
const ahora = () => AHORA;

const HORAS: Record<IdCapa, Date> = {
  satelite: new Date('2026-11-23T13:50:00Z'),
  lluvia: new Date('2026-11-23T09:30:00Z'),
  rayos: new Date('2026-11-23T14:15:00Z'),
};

const leerHoraFija = (capa: DefinicionCapa) => Promise.resolve(HORAS[capa.id]);

/** Mapa falso: guarda las props que recibe para comprobar qué se dibujaría. */
function crearMapaFalso() {
  const ultimas: { props: PropsMapa | null } = { props: null };
  function MapaFalso(props: PropsMapa) {
    ultimas.props = props;
    return <div data-testid="mapa">{props.capas.map((capa) => capa.id).join(',')}</div>;
  }
  return { MapaFalso, ultimas };
}

function interruptor(nombre: RegExp) {
  return screen.getByRole('checkbox', { name: nombre });
}

describe('SeccionMapa', () => {
  it('abre con Nubes y Rayos encendidas, Lluvia apagada, y dice de qué hora es cada imagen', async () => {
    const { MapaFalso } = crearMapaFalso();
    render(<SeccionMapa leerHora={leerHoraFija} ahora={ahora} Mapa={MapaFalso} />);

    expect(interruptor(/Nubes/)).toBeChecked();
    expect(interruptor(/Rayos/)).toBeChecked();
    expect(interruptor(/Lluvia/)).not.toBeChecked();
    expect(screen.getAllByText('Consultando la hora de la imagen…')).toHaveLength(2);
    expect(
      await screen.findByText('Imagen de las 8:50 a. m. (hora de Perú), hace 49 min'),
    ).toBeInTheDocument();
    expect(await screen.findByText(/Imagen de las 9:15 a. m./)).toBeInTheDocument();
    expect(screen.getByTestId('mapa')).toHaveTextContent('satelite,rayos');
  });

  it('avisa siempre que las imágenes llegan con retraso', () => {
    const { MapaFalso } = crearMapaFalso();
    render(<SeccionMapa leerHora={leerHoraFija} ahora={ahora} Mapa={MapaFalso} />);

    expect(
      screen.getByText('Imágenes de satélite con retraso. No es en vivo.'),
    ).toBeInTheDocument();
  });

  it('pasa al mapa la URL con la hora exacta consultada', async () => {
    const { MapaFalso, ultimas } = crearMapaFalso();
    render(<SeccionMapa leerHora={leerHoraFija} ahora={ahora} Mapa={MapaFalso} />);

    await screen.findByText(/Imagen de las 8:50/);
    expect(ultimas.props?.capas[0]?.url).toContain('/2026-11-23T13:50:00Z/');
  });

  it('enciende y apaga cada capa por separado, con el estado en texto', async () => {
    const { MapaFalso } = crearMapaFalso();
    render(
      <SeccionMapa
        leerHora={leerHoraFija}
        ahora={ahora}
        Mapa={MapaFalso}
        encendidasAlInicio={['satelite']}
      />,
    );
    await screen.findByText(/Imagen de las 8:50/);

    const rayos = interruptor(/Rayos/);
    expect(rayos.closest('label')).toHaveTextContent('Apagada');

    fireEvent.click(rayos);
    expect(rayos).toBeChecked();
    expect(rayos.closest('label')).toHaveTextContent('Encendida');
    expect(await screen.findByText(/Imagen de las 9:15 a. m./)).toBeInTheDocument();
    expect(screen.getByTestId('mapa')).toHaveTextContent('satelite,rayos');

    fireEvent.click(interruptor(/Nubes/));
    expect(screen.getByTestId('mapa')).toHaveTextContent(/^rayos$/);
    expect(screen.queryByText(/Imagen de las 8:50/)).not.toBeInTheDocument();
  });

  it('muestra la lluvia con su retraso real y la marca como antigua si pasa el umbral', async () => {
    const { MapaFalso } = crearMapaFalso();
    const leerHora = (capa: DefinicionCapa) =>
      Promise.resolve(capa.id === 'lluvia' ? new Date('2026-11-23T05:00:00Z') : HORAS[capa.id]);
    render(
      <SeccionMapa leerHora={leerHora} ahora={ahora} Mapa={MapaFalso} encendidasAlInicio={[]} />,
    );

    fireEvent.click(interruptor(/Lluvia/));

    expect(
      await screen.findByText('Imagen de las 12:00 a. m. (hora de Perú), hace 9 h'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Imagen antigua/)).toBeInTheDocument();
  });

  it('si no se puede consultar una capa, lo dice, no la dibuja y deja reintentar', async () => {
    const { MapaFalso } = crearMapaFalso();
    const leerHora = vi.fn((capa: DefinicionCapa) =>
      capa.id === 'rayos' ? Promise.reject(new Error('sin red')) : leerHoraFija(capa),
    );
    render(
      <SeccionMapa
        leerHora={leerHora}
        ahora={ahora}
        Mapa={MapaFalso}
        encendidasAlInicio={['satelite']}
      />,
    );
    await screen.findByText(/Imagen de las 8:50/);

    fireEvent.click(interruptor(/Rayos/));

    expect(await screen.findByText(/No pudimos consultar esta capa/)).toBeInTheDocument();
    expect(screen.getByTestId('mapa')).toHaveTextContent(/^satelite$/);

    leerHora.mockImplementation(leerHoraFija);
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText(/Imagen de las 9:15/)).toBeInTheDocument();
  });

  it('si el servicio no informa horas, no muestra la capa como si fuera actual', async () => {
    const { MapaFalso } = crearMapaFalso();
    render(<SeccionMapa leerHora={() => Promise.resolve(null)} ahora={ahora} Mapa={MapaFalso} />);

    expect(await screen.findAllByText(/no tiene imágenes recientes/)).toHaveLength(2);
    expect(screen.getByTestId('mapa')).toBeEmptyDOMElement();
  });

  it('avisa cuando fallan imágenes de una capa sin afectar a las demás', async () => {
    const { MapaFalso, ultimas } = crearMapaFalso();
    render(
      <SeccionMapa
        leerHora={leerHoraFija}
        ahora={ahora}
        Mapa={MapaFalso}
        encendidasAlInicio={['satelite', 'rayos']}
      />,
    );
    await screen.findByText(/Imagen de las 9:15/);

    act(() => ultimas.props?.alFallarCapa('rayos'));

    const rayos = screen.getByText(/Imagen de las 9:15/).parentElement;
    expect(rayos && within(rayos).getByText(/Algunas partes de esta capa/)).toBeInTheDocument();
    expect(screen.getAllByText(/Algunas partes de esta capa/)).toHaveLength(1);
  });

  it('avisa si el mapa base no carga', async () => {
    const { MapaFalso, ultimas } = crearMapaFalso();
    render(<SeccionMapa leerHora={leerHoraFija} ahora={ahora} Mapa={MapaFalso} />);
    await screen.findByText(/Imagen de las 8:50/);

    act(() => ultimas.props?.alFallarMapa('red'));

    expect(screen.getByRole('alert')).toHaveTextContent('No pudimos cargar el mapa base');
  });

  it('vuelve a consultar la hora de las capas encendidas cada cierto tiempo', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const { MapaFalso, ultimas } = crearMapaFalso();
      const leerHora = vi
        .fn<(capa: DefinicionCapa) => Promise<Date | null>>()
        .mockResolvedValueOnce(HORAS.satelite)
        .mockResolvedValue(new Date('2026-11-23T14:00:00Z'));
      render(
        <SeccionMapa
          leerHora={leerHora}
          ahora={ahora}
          Mapa={MapaFalso}
          refrescoMs={60_000}
          encendidasAlInicio={['satelite']}
        />,
      );
      await screen.findByText(/Imagen de las 8:50/);

      await act(() => vi.advanceTimersByTimeAsync(60_000));

      expect(await screen.findByText(/Imagen de las 9:00/)).toBeInTheDocument();
      expect(ultimas.props?.capas[0]?.url).toContain('/2026-11-23T14:00:00Z/');
    } finally {
      vi.useRealTimers();
    }
  });
});
