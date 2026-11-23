/**
 * Textos de los estados de datos, comunes a toda la app. Definidos por `ux-contenido`: se
 * usan literalmente.
 */
import {
  describirAntiguedadCompleta,
  describirMomento,
  describirMomentoConDe,
} from '../../comun/hora';
import type { Franja } from './estadoProducto';

export const TEXTOS_ESTADO = {
  cargando: 'Buscando los datos…',
  lenta: 'Está tardando. Puede ser tu señal.',
  sinDatos: 'Aún no tenemos estos datos. Estamos preparándolos.',
  sinConexionSinDato:
    'Sin conexión y todavía no hay datos guardados en este celular. Conéctate una vez para descargarlos.',
  error: 'No pudimos cargar los datos. No es tu culpa: inténtalo de nuevo en unos minutos.',
  faltaDato: 'Sin dato por ahora.',
  reintentar: 'Reintentar',
};

/** Cierra la frase con punto sin duplicarlo cuando termina en "a. m." o "p. m.". */
function conPunto(frase: string): string {
  return frase.endsWith('.') ? frase : `${frase}.`;
}

export function textoAntiguo(momento: Date, ahora: Date): string {
  return `${conPunto(`Dato ${describirMomentoConDe(momento, ahora)}`)} Puede haber cambiado.`;
}

export function textoSinConexion(momento: Date, ahora: Date): string {
  return conPunto(
    `Sin conexión. Te mostramos lo último guardado: ${describirMomento(momento, ahora)}`,
  );
}

/**
 * Hora del dato mostrado. PROVISIONAL: la especificación pide mostrar el dato "con su hora"
 * pero no da la frase; pendiente de `ux-contenido`.
 */
export function textoActualizado(momento: Date, ahora: Date): string {
  return conPunto(`Actualizado ${describirAntiguedadCompleta(momento, ahora)}`);
}

export function textoFranja(franja: Franja, ahora: Date): string {
  switch (franja.tipo) {
    case 'cargando':
      return TEXTOS_ESTADO.cargando;
    case 'lenta':
      return TEXTOS_ESTADO.lenta;
    case 'sin-datos':
      return TEXTOS_ESTADO.sinDatos;
    case 'sin-conexion-con-dato':
      return textoSinConexion(franja.momento, ahora);
    case 'sin-conexion-sin-dato':
      return TEXTOS_ESTADO.sinConexionSinDato;
    case 'error':
      return TEXTOS_ESTADO.error;
    case 'antiguo':
      return textoAntiguo(franja.momento, ahora);
  }
}
