import { useSyncExternalStore } from 'react';

/**
 * Navegación mínima por el fragmento de la URL (`#mapa`): funciona en GitHub Pages sin
 * configurar el servidor, respeta el botón Atrás y no necesita una librería de rutas.
 * Para añadir una sección basta con sumarla aquí y en `BarraNavegacion`.
 */
export const SECCIONES = [
  { id: 'inicio', nombre: 'Inicio' },
  { id: 'mapa', nombre: 'Mapa' },
] as const;

export type IdSeccion = (typeof SECCIONES)[number]['id'];

export function seccionDesdeFragmento(fragmento: string): IdSeccion {
  const id = fragmento.replace(/^#/, '');
  return SECCIONES.find((seccion) => seccion.id === id)?.id ?? 'inicio';
}

function suscribir(avisar: () => void) {
  window.addEventListener('hashchange', avisar);
  return () => window.removeEventListener('hashchange', avisar);
}

/** Sección activa según `location.hash`. */
export function useSeccion(): IdSeccion {
  return useSyncExternalStore(
    suscribir,
    () => seccionDesdeFragmento(window.location.hash),
    () => 'inicio',
  );
}
