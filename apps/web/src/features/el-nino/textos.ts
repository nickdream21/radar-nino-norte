/**
 * Textos de la pantalla El Niño. Definidos por `ux-contenido` y el meteorólogo del proyecto:
 * se usan literalmente. Los marcados PROVISIONAL no venían en la especificación.
 */
import { formatearAnomalia, formatearDecimal, signoAnomalia } from '../../comun/numeros';

export const TEXTOS_EL_NINO = {
  titulo: 'El Niño',

  // Bloque 1
  /** PROVISIONAL: título del bloque cuando no hay comunicado (la especificación no lo cubre). */
  estadoOficialSinDato: 'Estado oficial',
  leerComunicado: 'Leer el comunicado oficial',
  comunicadoAntiguo: 'Puede haber un comunicado más reciente.',

  // Bloque 2
  /** PROVISIONAL: la especificación no da título visible a este bloque. */
  tituloMar: 'El mar frente a Paita',
  /** PROVISIONAL: la especificación no da la fuente de este bloque; se sigue el patrón del bloque 4. */
  fuenteMar: 'Fuente: NOAA.',

  // Bloque 3
  tituloSignificado: '¿Qué significa para mí?',
  significado: [
    'Cuando el mar frente a la costa norte está más caliente, el aire tiene más humedad y las lluvias fuertes se vuelven más frecuentes durante semanas o meses.',
    'Pero el mar caliente no dice qué día ni en qué distrito va a llover. Puede haber días secos con el mar muy caliente.',
  ],
  /**
   * Última frase del bloque 3 y a dónde lleva. Cuando exista el semáforo por distrito, se
   * cambia aquí para que apunte a Mi distrito (`destino: 'mi-distrito'`).
   */
  significadoAccion: {
    texto: 'Para saber qué esperar donde vives, mira los ',
    enlace: 'avisos de SENAMHI',
    final: '.',
    destino: 'senamhi' as 'senamhi' | 'mi-distrito',
  },

  // Bloque 4
  tituloEspecialistas: 'Los números que usan los especialistas',
  tituloNino12: 'Esta semana (índice Niño 1+2)',
  tituloIcen: 'Promedio de tres meses (índice ICEN)',

  // Cierre
  cierre:
    'Nadie puede pronosticar con precisión cómo seguirá El Niño costero dentro de varios meses.',
};

export function textoEstadoOficial(estado: string): string {
  return `Estado oficial: ${estado}`;
}

export function textoExplicacionEnfen(fecha: string): string {
  return `Lo decide la comisión ENFEN, el grupo de instituciones del Estado que vigila El Niño. Comunicado del ${fecha}.`;
}

/**
 * `+8,9 °C más caliente que lo normal` / `−1,2 °C más frío que lo normal`.
 * PROVISIONAL para el cero (0,0 °C): la especificación no lo cubre y solo se muestra la cifra.
 */
export function partesCifraMar(anomalia: number): { cifra: string; comparacion: string | null } {
  const cifra = formatearAnomalia(anomalia);
  switch (signoAnomalia(anomalia)) {
    case 'positiva':
      return { cifra, comparacion: 'más caliente que lo normal' };
    case 'negativa':
      return { cifra, comparacion: 'más frío que lo normal' };
    case 'cero':
      return { cifra, comparacion: null };
  }
}

export function textoExplicacionMar(fecha: string): string {
  return `Es la temperatura del mar frente a Paita comparada con lo habitual en esta época. Dato del ${fecha}; llega con unos 2 días de retraso.`;
}

export function textoNino12(anomalia: number, temperatura: number, semana: string): string {
  return `${formatearAnomalia(anomalia)} sobre lo normal; el mar está a ${formatearDecimal(temperatura)} °C. Es una zona grande de mar frente a Ecuador y el norte del Perú. Semana del ${semana}. Fuente: NOAA.`;
}

/** El valor del ICEN se muestra como anomalía en °C, sin categoría (débil, fuerte…). */
export function textoIcen(valor: number, mes: string): string {
  return `${formatearAnomalia(valor)}. Es el número que usa el Perú para medir El Niño costero. Como promedia tres meses, va con retraso: este valor corresponde a ${mes}. Fuente: IGP.`;
}
