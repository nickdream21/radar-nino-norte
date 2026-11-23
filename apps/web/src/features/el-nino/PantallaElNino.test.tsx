import type { EstadoNino, ProductoPublicado } from '@radar/contratos';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { crearAlmacenFalso, crearEntornoFalso, crearRelojFalso } from '../../pruebas/dobles';
import type { Copia, Resultado } from '../estado/manifiesto';
import { esEstadoNino } from './estadoNino';
import { PantallaElNino } from './PantallaElNino';
import grabado from './respuestas/estado-nino-2026-11-23.json?raw';

const ESTADO: unknown = JSON.parse(grabado);
if (!esEstadoNino(ESTADO)) throw new Error('La respuesta grabada no es un EstadoNino válido');

/** Entrada del manifiesto publicado el 23 de noviembre. */
const PRODUCTO: ProductoPublicado = {
  id: 'estado-nino',
  ruta: 'nino/estado.json',
  fuente: 'NOAA CPC; IGP (ICEN, ENFEN); NOAA Coral Reef Watch; ENFEN',
  actualizado_en: '2026-11-21T12:00:00Z',
  vigencia_min: 5760,
};

const COPIA: Copia<EstadoNino> = { producto: PRODUCTO, datos: ESTADO };
const CLAVE = 'radar:producto:estado-nino';

const listo = (copia: Copia<EstadoNino> = COPIA): Resultado<EstadoNino> => ({
  tipo: 'listo',
  copia,
});

function montar({
  ahora = '2026-11-23T15:00:00Z',
  leer = vi.fn(() => Promise.resolve(listo())),
  enLinea = true,
  guardado,
}: {
  ahora?: string;
  leer?: () => Promise<Resultado<EstadoNino>>;
  enLinea?: boolean;
  guardado?: Copia<EstadoNino>;
} = {}) {
  const { reloj, avanzar } = crearRelojFalso(new Date(ahora));
  const red = crearEntornoFalso(enLinea);
  const almacen = crearAlmacenFalso(guardado ? { [CLAVE]: JSON.stringify(guardado) } : {});
  render(<PantallaElNino leer={leer} reloj={reloj} entorno={red.entorno} almacen={almacen} />);
  return { avanzar: (ms: number) => act(() => avanzar(ms)), red, almacen, leer };
}

const tarjeta = (titulo: RegExp) => {
  const encabezado = screen.getByRole('heading', { name: titulo });
  const seccion = encabezado.closest('section');
  if (!seccion) throw new Error(`Sin tarjeta para ${titulo}`);
  return within(seccion);
};

const conDatos = (cambios: Partial<EstadoNino>): Copia<EstadoNino> => ({
  producto: PRODUCTO,
  datos: { ...ESTADO, ...cambios },
});

describe('PantallaElNino', () => {
  it('muestra cada cifra con su explicación, la fecha de su dato y su fuente', async () => {
    montar();

    expect(
      await screen.findByRole('heading', { name: 'Estado oficial: Alerta de El Niño Costero' }),
    ).toBeInTheDocument();
    const oficial = tarjeta(/^Estado oficial: Alerta de El Niño Costero$/);
    expect(
      oficial.getByText(
        'Lo decide la comisión ENFEN, el grupo de instituciones del Estado que vigila El Niño. Comunicado del 13 de noviembre.',
      ),
    ).toBeInTheDocument();
    expect(oficial.getByRole('link', { name: /Leer el comunicado oficial/ })).toHaveAttribute(
      'href',
      'https://enfen.imarpe.gob.pe/',
    );
    expect(oficial.queryByText(/Puede haber un comunicado más reciente/)).not.toBeInTheDocument();

    const mar = tarjeta(/El mar frente a Paita/);
    expect(mar.getByText('+8,9 °C')).toBeInTheDocument();
    expect(mar.getByText('más caliente que lo normal')).toBeInTheDocument();
    expect(
      mar.getByText(
        'Es la temperatura del mar frente a Paita comparada con lo habitual en esta época. Dato del 21 de noviembre; llega con unos 2 días de retraso.',
      ),
    ).toBeInTheDocument();
    expect(mar.getByText('Fuente: NOAA.')).toBeInTheDocument();

    const nino12 = tarjeta(/Esta semana \(índice Niño 1\+2\)/);
    expect(
      nino12.getByText(
        '+5,7 °C sobre lo normal; el mar está a 27,5 °C. Es una zona grande de mar frente a Ecuador y el norte del Perú. Semana del 18 de noviembre. Fuente: NOAA.',
      ),
    ).toBeInTheDocument();

    const icen = tarjeta(/Promedio de tres meses \(índice ICEN\)/);
    expect(
      icen.getByText(
        '+4,5 °C. Es el número que usa el Perú para medir El Niño costero. Como promedia tres meses, va con retraso: este valor corresponde a septiembre de 2026. Fuente: IGP.',
      ),
    ).toBeInTheDocument();
  });

  it('pliega "Los números que usan los especialistas" por defecto', async () => {
    montar();
    const titulo = await screen.findByRole('heading', {
      name: 'Los números que usan los especialistas',
    });
    expect(titulo.closest('details')).not.toHaveAttribute('open');
  });

  it('explica qué significa sin desplegar nada y sin afirmar que lloverá', async () => {
    montar();
    const significado = tarjeta(/¿Qué significa para mí\?/);
    expect(
      significado.getByText(/Pero el mar caliente no dice qué día ni en qué distrito va a llover/),
    ).toBeInTheDocument();
    expect(significado.getByRole('link', { name: /avisos de SENAMHI/ })).toBeInTheDocument();
    expect(
      screen.getByText(
        'Nadie puede pronosticar con precisión cómo seguirá El Niño costero dentro de varios meses.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Radar Niño Norte no es una alerta oficial. Los avisos oficiales son de SENAMHI.',
        { exact: false },
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Acerca de y fuentes' })).toHaveAttribute(
      'href',
      '#/acerca',
    );
    await screen.findByRole('heading', { name: /Estado oficial/ });
  });

  it('un solo h1 y encabezados en orden', async () => {
    montar();
    await screen.findByRole('heading', { name: /Estado oficial/ });
    const niveles = screen.getAllByRole('heading').map((h) => Number(h.tagName.slice(1)));
    expect(niveles.filter((nivel) => nivel === 1)).toHaveLength(1);
    expect(niveles[0]).toBe(1);
    niveles.forEach((nivel, i) => {
      if (i > 0) expect(nivel - (niveles[i - 1] ?? 1)).toBeLessThanOrEqual(1);
    });
  });

  it('con el comunicado de hace más de 21 días advierte que puede haber otro', async () => {
    montar({ ahora: '2026-12-05T15:00:00Z' });
    expect(await screen.findByText('Puede haber un comunicado más reciente.')).toBeInTheDocument();
  });

  it('un bloque null dice "Sin dato por ahora." solo en su tarjeta', async () => {
    montar({ leer: () => Promise.resolve(listo(conDatos({ mar_paita: null, icen: null }))) });

    await screen.findByRole('heading', { name: /Estado oficial: Alerta/ });
    expect(tarjeta(/El mar frente a Paita/).getByText('Sin dato por ahora.')).toBeInTheDocument();
    expect(tarjeta(/índice ICEN/).getByText('Sin dato por ahora.')).toBeInTheDocument();
    expect(tarjeta(/índice Niño 1\+2/).getByText(/\+5,7 °C sobre lo normal/)).toBeInTheDocument();
    expect(screen.getAllByText('Sin dato por ahora.')).toHaveLength(2);
  });

  it('sin comunicado ENFEN no inventa un estado oficial', async () => {
    montar({ leer: () => Promise.resolve(listo(conDatos({ enfen: null }))) });
    const oficial = await screen.findByRole('heading', { name: 'Estado oficial' });
    expect(within(oficial.closest('section') as HTMLElement).getByText('Sin dato por ahora.'));
    expect(screen.queryByText(/Alerta/)).not.toBeInTheDocument();
  });

  it('mientras carga sin nada guardado no muestra cifras', () => {
    montar({ leer: () => new Promise(() => {}) });
    expect(screen.getByText('Buscando los datos…')).toBeInTheDocument();
    expect(screen.queryByText(/°C/)).not.toBeInTheDocument();
  });

  it('muestra al instante el dato guardado, con su hora, mientras busca uno nuevo', () => {
    montar({ leer: () => new Promise(() => {}), guardado: COPIA });
    expect(screen.getByText('Buscando los datos…')).toBeInTheDocument();
    expect(screen.getByText('+8,9 °C')).toBeInTheDocument();
    expect(
      screen.getByText('Actualizado hace 2 días, el 21 de noviembre a las 7:00 a. m.'),
    ).toBeInTheDocument();
  });

  it('si tarda más de 8 s ofrece reintentar', async () => {
    const leer = vi.fn(() => new Promise<Resultado<EstadoNino>>(() => {}));
    const { avanzar } = montar({ leer });
    avanzar(7_999);
    expect(screen.queryByText(/Está tardando/)).not.toBeInTheDocument();
    avanzar(1);
    expect(screen.getByText('Está tardando. Puede ser tu señal.')).toBeInTheDocument();

    leer.mockImplementation(() => Promise.resolve(listo()));
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('+8,9 °C')).toBeInTheDocument();
    expect(screen.queryByText(/Está tardando/)).not.toBeInTheDocument();
  });

  it('sin red y con dato guardado: franja "Sin conexión" con la hora del dato; al volver la red se actualiza sola', async () => {
    const leer = vi.fn(() => Promise.resolve(listo()));
    const viejo = conDatos({});
    viejo.producto = { ...PRODUCTO, actualizado_en: '2026-11-23T11:10:00Z' };
    const { red } = montar({ leer, enLinea: false, guardado: viejo });

    expect(
      screen.getByText('Sin conexión. Te mostramos lo último guardado: hoy a las 6:10 a. m.'),
    ).toBeInTheDocument();
    expect(screen.getByText('+8,9 °C')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
    expect(leer).not.toHaveBeenCalled();

    act(() => red.cambiarRed(true));
    expect(leer).toHaveBeenCalledTimes(1);
    expect(await screen.findByText(/Actualizado hace 2 días/)).toBeInTheDocument();
    expect(screen.queryByText(/Sin conexión/)).not.toBeInTheDocument();
  });

  it('sin red y sin dato guardado: texto propio y reintentar', () => {
    montar({ enLinea: false });
    expect(
      screen.getByText(
        'Sin conexión y todavía no hay datos guardados en este celular. Conéctate una vez para descargarlos.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
  });

  it('si la red se corta con la app abierta, lo dice', async () => {
    const { red } = montar();
    await screen.findByText('+8,9 °C');
    act(() => red.cambiarRed(false));
    expect(screen.getByText(/^Sin conexión\. Te mostramos lo último guardado/)).toBeInTheDocument();
  });

  it('error: texto distinto, reintentar y enlace a SENAMHI', async () => {
    const leer = vi.fn(() => Promise.resolve<Resultado<EstadoNino>>({ tipo: 'error' }));
    montar({ leer });

    const franja = (
      await screen.findByText(
        'No pudimos cargar los datos. No es tu culpa: inténtalo de nuevo en unos minutos.',
      )
    ).closest('[role="status"]') as HTMLElement;
    expect(within(franja).getByRole('link', { name: /Ver avisos de SENAMHI/ })).toHaveAttribute(
      'href',
      'https://www.senamhi.gob.pe/?p=aviso-meteorologico',
    );
    expect(screen.queryByText(/Sin conexión/)).not.toBeInTheDocument();

    leer.mockImplementation(() => Promise.resolve(listo()));
    fireEvent.click(within(franja).getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('+8,9 °C')).toBeInTheDocument();
    expect(leer).toHaveBeenCalledTimes(2);
  });

  it('guarda el dato recibido para la próxima vez', async () => {
    const { almacen } = montar();
    await screen.findByText('+8,9 °C');
    expect(JSON.parse(almacen.contenido.get(CLAVE) ?? 'null')).toEqual(COPIA);
  });

  it('la antigüedad no se congela con la app abierta y el dato pasa a antiguo al vencer', async () => {
    const reciente: Copia<EstadoNino> = {
      producto: { ...PRODUCTO, actualizado_en: '2026-11-23T14:50:00Z', vigencia_min: 180 },
      datos: ESTADO,
    };
    const { avanzar } = montar({ leer: () => Promise.resolve(listo(reciente)) });
    expect(await screen.findByText('Actualizado hace 10 min.')).toBeInTheDocument();

    avanzar(5 * 60_000);
    expect(screen.getByText('Actualizado hace 15 min.')).toBeInTheDocument();

    avanzar(2 * 60 * 60_000);
    expect(screen.getByText('Actualizado hace 2 h, hoy a las 9:50 a. m.')).toBeInTheDocument();
    expect(screen.queryByText(/Puede haber cambiado/)).not.toBeInTheDocument();

    avanzar(60 * 60_000);
    expect(
      screen.getByText('Dato de hoy a las 9:50 a. m. Puede haber cambiado.'),
    ).toBeInTheDocument();
  });

  it('vuelve a consultar al regresar la app a primer plano', async () => {
    const { red, leer } = montar();
    await screen.findByText('+8,9 °C');
    expect(leer).toHaveBeenCalledTimes(1);
    act(() => red.volverAPrimerPlano());
    expect(leer).toHaveBeenCalledTimes(2);
    await screen.findByText('+8,9 °C');
  });

  it('con un dato vencido lo muestra marcado como antiguo, antes del contenido', async () => {
    montar({ ahora: '2026-11-26T15:00:00Z' });
    const aviso = await screen.findByText(
      'Dato del 21 de noviembre a las 7:00 a. m. Puede haber cambiado.',
    );
    const cifra = screen.getByText('+8,9 °C');
    expect(aviso.compareDocumentPosition(cifra) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(aviso.closest('[role="status"]')).not.toBeNull();
  });
});
