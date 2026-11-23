import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { crearAlmacenFalso } from '../../pruebas/dobles';
import type { Coordenadas } from './geo';
import { PantallaMiDistrito } from './PantallaMiDistrito';
import { CLAVE_DISTRITO, crearPreferenciaDistrito } from './preferencia';
import type { Geolocalizador } from './ubicacion';

/** Geolocalización controlada por la prueba: nunca toca la del navegador. */
function crearGeolocalizadorFalso() {
  let resolver: (punto: Coordenadas) => void = () => {};
  let rechazar: (error: Error) => void = () => {};
  const obtener = vi.fn(
    () =>
      new Promise<Coordenadas>((si, no) => {
        resolver = si;
        rechazar = no;
      }),
  );
  const geolocalizador: Geolocalizador = { obtener };
  return {
    geolocalizador,
    obtener,
    responder: async (punto: Coordenadas) => act(async () => resolver(punto)),
    fallar: async () => act(async () => rechazar(new Error('permiso denegado'))),
  };
}

function montar(inicial: Record<string, string> = {}) {
  const almacen = crearAlmacenFalso(inicial);
  const geo = crearGeolocalizadorFalso();
  render(
    <PantallaMiDistrito
      preferencia={crearPreferenciaDistrito(almacen)}
      geolocalizador={geo.geolocalizador}
    />,
  );
  return { almacen, geo };
}

const titulo = () => screen.getByRole('heading', { level: 1 });
const buscador = () => screen.getByRole('searchbox', { name: 'Busca tu distrito' });
const escribir = (texto: string) => fireEvent.change(buscador(), { target: { value: texto } });

describe('PantallaMiDistrito sin distrito guardado', () => {
  it('pide elegir distrito con el texto de la especificación', () => {
    montar();
    expect(titulo()).toHaveTextContent('¿Dónde vives?');
    expect(
      screen.getByText(
        'Elige tu distrito para ver la lluvia que se espera ahí. Puedes cambiarlo cuando quieras.',
      ),
    ).toBeInTheDocument();
    expect(buscador()).toBeInTheDocument();
  });

  it('busca, anuncia los resultados y guarda solo el ubigeo al elegir', async () => {
    const { almacen } = montar();
    escribir('  CAÑARIS ');

    const resultados = await screen.findByRole('list', { name: 'Resultados de la búsqueda' });
    const opciones = within(resultados).getAllByRole('button');
    expect(opciones.map((o) => o.textContent)).toEqual(['Cañaris — Ferreñafe, Lambayeque']);
    // El número de resultados se anuncia desde una región viva.
    expect(screen.getByText('1 distrito encontrado.').closest('[role="status"]')).not.toBeNull();

    fireEvent.click(
      within(resultados).getByRole('button', { name: 'Cañaris — Ferreñafe, Lambayeque' }),
    );
    expect(titulo()).toHaveTextContent('Cañaris');
    expect(titulo()).toHaveFocus();
    expect(screen.getByText('Ferreñafe, Lambayeque')).toBeInTheDocument();
    expect(Object.fromEntries(almacen.contenido)).toEqual({ [CLAVE_DISTRITO]: '140202' });
  });

  it('muestra el aviso cuando no hay resultados', async () => {
    montar();
    escribir('Lima');
    expect(
      await screen.findByText(
        'No encontramos ese distrito. Prueba con otro nombre o búscalo en la lista.',
      ),
    ).toBeInTheDocument();
  });

  it('la lista en tres pasos lleva el foco al título de cada paso', () => {
    const { almacen } = montar();
    const lista = within(screen.getByRole('region', { name: 'O elige de la lista' }));
    expect(lista.getAllByRole('button').map((b) => b.textContent)).toEqual([
      'Cajamarca',
      'La Libertad',
      'Lambayeque',
      'Piura',
      'Tumbes',
    ]);

    fireEvent.click(lista.getByRole('button', { name: 'Lambayeque' }));
    expect(titulo()).toHaveTextContent('Provincias de Lambayeque');
    expect(titulo()).toHaveFocus();
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual([
      'Volver',
      'Chiclayo',
      'Ferreñafe',
      'Lambayeque',
    ]);

    fireEvent.click(screen.getByRole('button', { name: 'Ferreñafe' }));
    expect(titulo()).toHaveTextContent('Distritos de la provincia de Ferreñafe');
    expect(titulo()).toHaveFocus();

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(titulo()).toHaveTextContent('Provincias de Lambayeque');
    fireEvent.click(screen.getByRole('button', { name: 'Ferreñafe' }));

    fireEvent.click(screen.getByRole('button', { name: 'Cañaris' }));
    expect(titulo()).toHaveTextContent('Cañaris');
    expect(titulo()).toHaveFocus();
    expect(almacen.contenido.get(CLAVE_DISTRITO)).toBe('140202');
  });
});

describe('Usar mi ubicación', () => {
  it('solo pide la ubicación al pulsar y siempre pide confirmar', async () => {
    const { geo, almacen } = montar();
    expect(geo.obtener).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }));
    expect(geo.obtener).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Buscando tu ubicación…')).toBeInTheDocument();
    // Pulsar otra vez mientras busca no repite la petición.
    fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }));
    expect(geo.obtener).toHaveBeenCalledTimes(1);

    await geo.responder({ latitud: -5.153, longitud: -80.657 });
    expect(titulo()).toHaveTextContent('¿Estás en Piura, Piura?');
    expect(titulo()).toHaveFocus();
    // Nada se guarda hasta confirmar, y la ubicación nunca.
    expect(almacen.contenido.size).toBe(0);

    fireEvent.click(screen.getByRole('button', { name: 'Sí, es mi distrito' }));
    expect(titulo()).toHaveTextContent('Piura');
    expect(Object.fromEntries(almacen.contenido)).toEqual({ [CLAVE_DISTRITO]: '200101' });
  });

  it('"No, elegir otro" vuelve al selector', async () => {
    const { geo, almacen } = montar();
    fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }));
    await geo.responder({ latitud: -5.153, longitud: -80.657 });

    fireEvent.click(screen.getByRole('button', { name: 'No, elegir otro' }));
    expect(titulo()).toHaveTextContent('¿Dónde vives?');
    expect(titulo()).toHaveFocus();
    expect(almacen.contenido.size).toBe(0);
  });

  it('fuera de la zona lo dice y deja elegir de la lista', async () => {
    const { geo } = montar();
    fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }));
    await geo.responder({ latitud: -12.046, longitud: -77.043 });
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Parece que estás fuera de la zona que cubre la app. Elige un distrito de la lista.',
    );
    expect(titulo()).toHaveTextContent('¿Dónde vives?');
  });

  it('si se niega el permiso o falla, lo dice sin bloquear', async () => {
    const { geo } = montar();
    fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }));
    await geo.fallar();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'No pudimos saber tu ubicación. Elige tu distrito de la lista.',
    );
    expect(buscador()).toBeEnabled();
  });
});

describe('PantallaMiDistrito con distrito guardado', () => {
  it('muestra el distrito, su provincia y departamento, y el aviso de pronóstico en preparación', () => {
    montar({ [CLAVE_DISTRITO]: '200101' });
    expect(titulo()).toHaveTextContent('Piura');
    expect(screen.getByText('Piura, Piura')).toBeInTheDocument();
    expect(
      screen.getByText(/Estamos preparando el pronóstico de lluvia por distrito\./),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Ver avisos de SENAMHI/ })).toBeInTheDocument();
  });

  it('"Cambiar distrito" abre el selector y se puede volver sin cambiar', () => {
    const { almacen } = montar({ [CLAVE_DISTRITO]: '200101' });
    fireEvent.click(screen.getByRole('button', { name: 'Cambiar distrito' }));
    expect(titulo()).toHaveTextContent('¿Dónde vives?');
    expect(titulo()).toHaveFocus();

    fireEvent.click(screen.getByRole('button', { name: 'Seguir con mi distrito' }));
    expect(titulo()).toHaveTextContent('Piura');
    expect(almacen.contenido.get(CLAVE_DISTRITO)).toBe('200101');
  });

  it('un ubigeo guardado que ya no existe vuelve al selector sin error', () => {
    montar({ [CLAVE_DISTRITO]: '999999' });
    expect(titulo()).toHaveTextContent('¿Dónde vives?');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Seguir con mi distrito' }),
    ).not.toBeInTheDocument();
  });

  it('si el almacenamiento falla, la elección dura la sesión', () => {
    const preferencia = crearPreferenciaDistrito({
      leer: () => null,
      guardar: () => {},
    });
    const geo = crearGeolocalizadorFalso();
    const { unmount } = render(
      <PantallaMiDistrito preferencia={preferencia} geolocalizador={geo.geolocalizador} />,
    );
    escribir('cañaris');
    fireEvent.click(screen.getByRole('button', { name: 'Cañaris — Ferreñafe, Lambayeque' }));
    unmount();

    // Volver a la sección (otro montaje) en la misma sesión.
    render(<PantallaMiDistrito preferencia={preferencia} geolocalizador={geo.geolocalizador} />);
    expect(titulo()).toHaveTextContent('Cañaris');
  });
});
