/**
 * Capas de tiempo de terceros que se dibujan sobre el mapa y cómo construir sus URL.
 *
 * Son servicios listos para el navegador (ver docs/arquitectura.md), no productos del
 * pipeline: por eso no tienen contrato en `@radar/contratos`.
 */

export type IdCapa = 'satelite' | 'lluvia' | 'rayos';

/** Rectángulo en grados: [oeste, sur, este, norte]. */
export type Rectangulo = readonly [number, number, number, number];

/** Zona de trabajo: Tumbes, Piura, Lambayeque, La Libertad y Cajamarca. */
export const ZONA_TRABAJO: Rectangulo = [-82, -9, -77, -3];

/** Hasta dónde se puede mover el mapa: la zona de trabajo y un entorno razonable. */
export const LIMITES_MAPA: Rectangulo = [-88, -13, -71, 1];

interface BaseCapa {
  id: IdCapa;
  /** Atribución que exige la fuente (HTML que muestra el control de MapLibre). */
  atribucion: string;
  /** Pasado este tiempo desde la hora de la imagen, se marca como antigua. */
  antiguaTrasMin: number;
  /** Zoom máximo al que el servicio entrega teselas; por encima se amplían. */
  zoomMaximo: number;
  opacidad: number;
}

export interface CapaGibs extends BaseCapa {
  servicio: 'gibs';
  capaGibs: string;
}

export interface CapaWms extends BaseCapa {
  servicio: 'wms';
  urlServicio: string;
  capaWms: string;
}

export type DefinicionCapa = CapaGibs | CapaWms;

const RAIZ_GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';
const MATRIZ_GIBS = 'GoogleMapsCompatible_Level6';

const ATRIBUCION_GIBS =
  '<a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noreferrer">NASA GIBS</a>';
const ATRIBUCION_NOWCOAST =
  '<a href="https://nowcoast.noaa.gov" target="_blank" rel="noreferrer">NOAA nowCOAST</a>';

/** En el orden en que se apilan: la primera queda abajo. */
export const CAPAS: readonly DefinicionCapa[] = [
  {
    id: 'satelite',
    servicio: 'gibs',
    capaGibs: 'GOES-East_ABI_Band13_Clean_Infrared',
    atribucion: ATRIBUCION_GIBS,
    // Llega con 40–65 min de retraso cada 10 min; dos horas ya es un hueco del servicio.
    antiguaTrasMin: 120,
    zoomMaximo: 6,
    opacidad: 0.7,
  },
  {
    id: 'lluvia',
    servicio: 'gibs',
    capaGibs: 'IMERG_Precipitation_Rate_30min',
    atribucion: ATRIBUCION_GIBS,
    // IMERG temprano se publica con unas 4–6 h de retraso.
    antiguaTrasMin: 8 * 60,
    zoomMaximo: 6,
    opacidad: 0.8,
  },
  {
    id: 'rayos',
    servicio: 'wms',
    urlServicio: 'https://nowcoast.noaa.gov/geoserver/observations/lightning_detection/ows',
    capaWms: 'ldn_lightning_strike_density',
    atribucion: ATRIBUCION_NOWCOAST,
    // Una imagen cada 15 min con unos 20–30 min de retraso.
    antiguaTrasMin: 60,
    zoomMaximo: 8,
    opacidad: 1,
  },
];

/** `2026-11-23T13:50:00Z`: el formato de la dimensión de tiempo de GIBS. */
export function formatearInstanteGibs(tiempo: Date): string {
  return tiempo.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function formatearDia(tiempo: Date): string {
  return tiempo.toISOString().slice(0, 10);
}

const DIA_MS = 24 * 60 * 60 * 1000;

/** Plantilla de teselas XYZ de GIBS para una hora exacta. */
export function urlTeselasGibs(capaGibs: string, tiempo: Date): string {
  return `${RAIZ_GIBS}/${capaGibs}/default/${formatearInstanteGibs(tiempo)}/${MATRIZ_GIBS}/{z}/{y}/{x}.png`;
}

/**
 * Consulta "DescribeDomains" de GIBS: devuelve los tiempos disponibles entre dos días antes
 * y un día después de `ahora`. Se pide por días para que la caché del servicio sirva a todos.
 */
export function urlDominiosGibs(capaGibs: string, ahora: Date): string {
  const desde = formatearDia(new Date(ahora.getTime() - 2 * DIA_MS));
  const hasta = formatearDia(new Date(ahora.getTime() + DIA_MS));
  return `${RAIZ_GIBS}/1.0.0/${capaGibs}/default/${MATRIZ_GIBS}/all/${desde}--${hasta}.xml`;
}

export function urlCapacidadesWms(urlServicio: string): string {
  return `${urlServicio}?service=WMS&version=1.3.0&request=GetCapabilities`;
}

/**
 * Plantilla de teselas WMS para MapLibre. `{bbox-epsg-3857}` lo sustituye MapLibre, así que
 * no se codifica. El tiempo se pide explícito: sin él, el servicio entrega la imagen más
 * cercana que tenga y no sabríamos de qué hora es.
 */
export function urlTeselasWms(urlServicio: string, capaWms: string, tiempo: Date): string {
  const parametros = [
    'service=WMS',
    'version=1.3.0',
    'request=GetMap',
    `layers=${capaWms}`,
    'styles=',
    'format=image/png',
    'transparent=true',
    'crs=EPSG:3857',
    'width=256',
    'height=256',
    `time=${tiempo.toISOString()}`,
    'bbox={bbox-epsg-3857}',
  ];
  return `${urlServicio}?${parametros.join('&')}`;
}

export function urlTeselas(capa: DefinicionCapa, tiempo: Date): string {
  return capa.servicio === 'gibs'
    ? urlTeselasGibs(capa.capaGibs, tiempo)
    : urlTeselasWms(capa.urlServicio, capa.capaWms, tiempo);
}

/** URL que informa de qué horas hay imágenes de la capa. */
export function urlHorasDisponibles(capa: DefinicionCapa, ahora: Date): string {
  return capa.servicio === 'gibs'
    ? urlDominiosGibs(capa.capaGibs, ahora)
    : urlCapacidadesWms(capa.urlServicio);
}
