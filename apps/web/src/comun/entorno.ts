/**
 * Lo que la app necesita saber del navegador para decidir cuándo volver a consultar los datos.
 * Inyectable para probar sin depender del estado real de la red.
 */
export type EventoEntorno = 'en-linea' | 'fuera-de-linea' | 'primer-plano';

export interface Entorno {
  enLinea(): boolean;
  /** Avisa cuando ocurre `evento`. Devuelve la función que deja de escuchar. */
  escuchar(evento: EventoEntorno, accion: () => void): () => void;
}

export const entornoNavegador: Entorno = {
  enLinea: () => navigator.onLine,
  escuchar: (evento, accion) => {
    if (evento === 'primer-plano') {
      const alCambiar = () => {
        if (document.visibilityState === 'visible') accion();
      };
      document.addEventListener('visibilitychange', alCambiar);
      return () => document.removeEventListener('visibilitychange', alCambiar);
    }
    const nombre = evento === 'en-linea' ? 'online' : 'offline';
    window.addEventListener(nombre, accion);
    return () => window.removeEventListener(nombre, accion);
  },
};
