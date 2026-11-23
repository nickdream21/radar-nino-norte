/**
 * Copia local del último dato válido de cada producto, para mostrarlo al instante al abrir la
 * app y cuando no hay conexión. El service worker también guarda las respuestas, pero no le
 * dice a la app si lo que entrega viene de la red o de su caché; esta copia sí lo sabe.
 */
export interface Almacen {
  leer(clave: string): string | null;
  guardar(clave: string, valor: string): void;
}

/** `localStorage` puede no existir o fallar (modo privado, cuota llena): se trata como vacío. */
export const almacenNavegador: Almacen = {
  leer: (clave) => {
    try {
      return window.localStorage.getItem(clave);
    } catch {
      return null;
    }
  },
  guardar: (clave, valor) => {
    try {
      window.localStorage.setItem(clave, valor);
    } catch {
      // Sin espacio o sin permiso: la app sigue funcionando, solo sin copia guardada.
    }
  },
};
