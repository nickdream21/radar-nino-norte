import { describe, expect, it } from 'vitest';
import {
  CAPAS,
  formatearInstanteGibs,
  urlDominiosGibs,
  urlHorasDisponibles,
  urlTeselas,
  urlTeselasGibs,
  urlTeselasWms,
  type IdCapa,
} from './capas';

const TIEMPO = new Date('2026-11-23T13:50:00Z');
const capa = (id: IdCapa) => {
  const encontrada = CAPAS.find((candidata) => candidata.id === id);
  if (!encontrada) throw new Error(id);
  return encontrada;
};

describe('URL de NASA GIBS', () => {
  it('formatea el instante sin milisegundos', () => {
    expect(formatearInstanteGibs(new Date('2026-11-23T08:30:00.000Z'))).toBe(
      '2026-11-23T08:30:00Z',
    );
  });

  it('pide las teselas de una hora exacta, en EPSG:3857 y orden z/y/x', () => {
    expect(urlTeselasGibs('GOES-East_ABI_Band13_Clean_Infrared', TIEMPO)).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GOES-East_ABI_Band13_Clean_Infrared/default/2026-11-23T13:50:00Z/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
    );
  });

  it('consulta las horas disponibles de dos días antes a un día después, por días', () => {
    expect(urlDominiosGibs('IMERG_Precipitation_Rate_30min', TIEMPO)).toBe(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/IMERG_Precipitation_Rate_30min/default/GoogleMapsCompatible_Level6/all/2026-11-21--2026-11-24.xml',
    );
  });
});

describe('URL de NOAA nowCOAST', () => {
  const servicio = 'https://nowcoast.noaa.gov/geoserver/observations/lightning_detection/ows';

  it('pide un GetMap con hora explícita y deja la caja para MapLibre', () => {
    const url = urlTeselasWms(servicio, 'ldn_lightning_strike_density', TIEMPO);
    const consulta = new URL(url.replace('{bbox-epsg-3857}', 'CAJA')).searchParams;

    expect(url.startsWith(`${servicio}?`)).toBe(true);
    expect(url).toContain('bbox={bbox-epsg-3857}');
    expect(Object.fromEntries(consulta)).toEqual({
      service: 'WMS',
      version: '1.3.0',
      request: 'GetMap',
      layers: 'ldn_lightning_strike_density',
      styles: '',
      format: 'image/png',
      transparent: 'true',
      crs: 'EPSG:3857',
      width: '256',
      height: '256',
      time: '2026-11-23T13:50:00.000Z',
      bbox: 'CAJA',
    });
  });

  it('consulta las horas disponibles en el GetCapabilities', () => {
    expect(urlHorasDisponibles(capa('rayos'), TIEMPO)).toBe(
      `${servicio}?service=WMS&version=1.3.0&request=GetCapabilities`,
    );
  });
});

describe('capas configuradas', () => {
  it('usa las capas verificadas de cada servicio', () => {
    expect(urlTeselas(capa('satelite'), TIEMPO)).toContain('/GOES-East_ABI_Band13_Clean_Infrared/');
    expect(urlTeselas(capa('lluvia'), TIEMPO)).toContain('/IMERG_Precipitation_Rate_30min/');
    expect(urlTeselas(capa('rayos'), TIEMPO)).toContain('layers=ldn_lightning_strike_density');
  });

  it('cada capa declara su atribución', () => {
    expect(capa('satelite').atribucion).toContain('NASA GIBS');
    expect(capa('lluvia').atribucion).toContain('NASA GIBS');
    expect(capa('rayos').atribucion).toContain('NOAA');
  });

  it('las de GIBS no piden teselas por encima del nivel 6', () => {
    expect(capa('satelite').zoomMaximo).toBe(6);
    expect(capa('lluvia').zoomMaximo).toBe(6);
  });
});
