import { useSyncExternalStore } from 'react';

/**
 * Navegación mínima por el fragmento de la URL (`#/mapa`): funciona en GitHub Pages sin
 * configurar el servidor y no necesita una librería de rutas para cuatro pantallas.
 */
export const SECCIONES = {
  'mi-distrito': { ruta: '#/', nombre: 'Mi distrito' },
  mapa: { ruta: '#/mapa', nombre: 'Mapa' },
  'el-nino': { ruta: '#/el-nino', nombre: 'El Niño' },
  acerca: { ruta: '#/acerca', nombre: 'Acerca de y fuentes' },
} as const;

export type IdSeccion = keyof typeof SECCIONES;

/** Secciones de la barra inferior, en orden. "Acerca" se enlaza desde las pantallas. */
export const SECCIONES_BARRA: readonly IdSeccion[] = ['mi-distrito', 'mapa', 'el-nino'];

const INICIO: IdSeccion = 'mi-distrito';

/** Acepta `#/mapa` y también `#mapa`, el formato de la versión anterior. */
export function seccionDesdeFragmento(fragmento: string): IdSeccion {
  const id = fragmento.replace(/^#\/?/, '');
  return Object.hasOwn(SECCIONES, id) ? (id as IdSeccion) : INICIO;
}

/**
 * El historial se mantiene en dos niveles, Mi distrito y la sección abierta encima, para que
 * el botón Atrás del teléfono siempre vuelva a Mi distrito y no recorra todas las pestañas.
 */
interface EstadoHistorial {
  radarNivel: 0 | 1;
}

const EVENTO = 'radar:navegacion';

function nivelActual(historia: History): 0 | 1 | null {
  const estado = historia.state as Partial<EstadoHistorial> | null;
  return estado?.radarNivel ?? null;
}

/** Al abrir la app directamente en una sección, pone Mi distrito debajo en el historial. */
export function prepararHistorial(
  historia: History = window.history,
  ubicacion: Location = window.location,
) {
  if (nivelActual(historia) !== null) return;
  const seccion = seccionDesdeFragmento(ubicacion.hash);
  historia.replaceState({ radarNivel: 0 } satisfies EstadoHistorial, '', SECCIONES[INICIO].ruta);
  if (seccion !== INICIO) {
    historia.pushState({ radarNivel: 1 } satisfies EstadoHistorial, '', SECCIONES[seccion].ruta);
  }
}

export function navegar(
  destino: IdSeccion,
  historia: History = window.history,
  ubicacion: Location = window.location,
) {
  const actual = seccionDesdeFragmento(ubicacion.hash);
  if (destino === actual) return;
  const ruta = SECCIONES[destino].ruta;
  if (destino === INICIO) {
    if (nivelActual(historia) === 1) {
      historia.back();
      return;
    }
    historia.replaceState({ radarNivel: 0 } satisfies EstadoHistorial, '', ruta);
  } else if (actual === INICIO) {
    historia.pushState({ radarNivel: 1 } satisfies EstadoHistorial, '', ruta);
  } else {
    historia.replaceState({ radarNivel: 1 } satisfies EstadoHistorial, '', ruta);
  }
  window.dispatchEvent(new Event(EVENTO));
}

function suscribir(avisar: () => void) {
  const eventos = ['hashchange', 'popstate', EVENTO];
  for (const evento of eventos) window.addEventListener(evento, avisar);
  return () => {
    for (const evento of eventos) window.removeEventListener(evento, avisar);
  };
}

/** Sección activa según `location.hash`. */
export function useSeccion(): IdSeccion {
  return useSyncExternalStore(
    suscribir,
    () => seccionDesdeFragmento(window.location.hash),
    () => INICIO,
  );
}
