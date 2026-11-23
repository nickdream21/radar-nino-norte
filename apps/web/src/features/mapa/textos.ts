/**
 * Textos provisionales de la sección Mapa, reunidos aquí para que `ux-contenido` los
 * revise y cambie sin tocar la lógica.
 */
import type { IdCapa } from './capas';
import {
  conArticulo,
  describirAntiguedad,
  describirDiaCorto,
  formatearHoraLima,
} from '../../comun/hora';

export const TEXTOS_CAPAS: Record<IdCapa, { nombre: string; descripcion: string }> = {
  satelite: {
    nombre: 'Nubes',
    descripcion: 'Satélite infrarrojo. Las nubes altas y frías, típicas de tormenta, resaltan.',
  },
  lluvia: {
    nombre: 'Lluvia',
    descripcion:
      'Estimación por satélite, promedio de 30 minutos. Llega con unas 4 a 6 h de retraso.',
  },
  rayos: {
    nombre: 'Rayos',
    descripcion: 'Densidad de rayos detectados en unos 15 minutos.',
  },
};

export const TEXTOS_MAPA = {
  titulo: 'Mapa',
  retraso: 'Imágenes de satélite con retraso. No es en vivo.',
  etiquetaMapa: 'Mapa del norte del Perú con capas de tiempo',
  tituloCapas: 'Capas',
  encendida: 'Encendida',
  apagada: 'Apagada',
  consultandoHora: 'Consultando la hora de la imagen…',
  sinDatos: 'El servicio no tiene imágenes recientes de esta capa. No la mostramos.',
  errorHora:
    'No pudimos consultar esta capa. Revisa tu conexión. El resto del mapa sigue funcionando.',
  errorImagen: 'Algunas partes de esta capa no cargaron. Revisa tu conexión.',
  reintentar: 'Reintentar',
  antigua: 'Imagen antigua: el servicio no se ha actualizado.',
  cargandoMapa: 'Cargando el mapa…',
  errorCodigoMapa: 'No pudimos abrir el mapa. Revisa tu conexión e inténtalo de nuevo.',
  errorMapa: 'No pudimos cargar el mapa base. Revisa tu conexión.',
  errorMapaNoSoportado: 'No pudimos abrir el mapa en este equipo.',
};

/**
 * `Imagen de las 8:50 a. m. (hora de Perú), hace 49 min`. Si la hora de la imagen queda en
 * el futuro (reloj del teléfono atrasado), se da solo la hora absoluta.
 */
export function textoHoraImagen(tiempo: Date, ahora: Date): string {
  const dia = describirDiaCorto(tiempo, ahora);
  const hora = conArticulo(formatearHoraLima(tiempo));
  const cuando =
    dia === null ? `de ${hora}` : dia === 'ayer' ? `de ayer a ${hora}` : `del ${dia} a ${hora}`;
  const antiguedad = describirAntiguedad(tiempo, ahora);
  return `Imagen ${cuando} (hora de Perú)${antiguedad ? `, ${antiguedad}` : ''}`;
}
