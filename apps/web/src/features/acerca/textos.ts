/**
 * Textos de "Acerca de y fuentes". El texto de presentación lo definió `ux-contenido`.
 * PROVISIONAL: la especificación nombra las fuentes pero no la frase de cada atribución;
 * se da solo el nombre, qué aporta y su sitio, pendiente de revisión.
 */
export const TEXTOS_ACERCA = {
  titulo: 'Acerca de y fuentes',
  presentacion:
    'Esta app es un proyecto gratuito e independiente. Calcula probabilidades con datos públicos y puede equivocarse. No reemplaza los avisos de SENAMHI ni las indicaciones de INDECI y de tu municipalidad.',
  tituloFuentes: 'Fuentes de los datos',
};

export const FUENTES: readonly { nombre: string; aporta: string; url: string }[] = [
  {
    nombre: 'Open-Meteo',
    aporta: 'Pronósticos del tiempo.',
    url: 'https://open-meteo.com/',
  },
  {
    nombre: 'NOAA',
    aporta: 'Temperatura del mar (índices Niño y Coral Reef Watch) y rayos (nowCOAST).',
    url: 'https://www.noaa.gov/',
  },
  {
    nombre: 'NASA',
    aporta: 'Imágenes de satélite de nubes y lluvia (GIBS).',
    url: 'https://earthdata.nasa.gov/gibs',
  },
  {
    nombre: 'IGP',
    aporta: 'Índice Costero El Niño (ICEN).',
    url: 'https://www.igp.gob.pe/',
  },
  {
    nombre: 'ENFEN',
    aporta: 'Comunicados oficiales sobre El Niño costero.',
    url: 'https://enfen.imarpe.gob.pe/',
  },
  {
    nombre: 'OpenFreeMap',
    aporta: 'Mapa base, con datos de OpenStreetMap y OpenMapTiles.',
    url: 'https://openfreemap.org/',
  },
];
