import { almacenNavegador, type Almacen } from '../estado/almacen';

/** Clave del almacenamiento local. Solo se guarda el ubigeo, nunca la ubicación. */
export const CLAVE_DISTRITO = 'radar:distrito';

/** Distrito elegido por la persona. */
export interface PreferenciaDistrito {
  leer(): string | null;
  guardar(ubigeo: string): void;
}

/**
 * Guarda el ubigeo en `almacen` y además lo recuerda en memoria: si el almacenamiento falla
 * (modo privado, cuota llena), la elección dura al menos lo que dure la sesión.
 */
export function crearPreferenciaDistrito(almacen: Almacen): PreferenciaDistrito {
  let enSesion: string | null = null;
  return {
    leer: () => enSesion ?? almacen.leer(CLAVE_DISTRITO),
    guardar: (ubigeo) => {
      enSesion = ubigeo;
      almacen.guardar(CLAVE_DISTRITO, ubigeo);
    },
  };
}

/** Una sola instancia para toda la app: sobrevive a cambiar de sección. */
export const preferenciaNavegador = crearPreferenciaDistrito(almacenNavegador);
