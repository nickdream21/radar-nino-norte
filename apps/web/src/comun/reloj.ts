import { useEffect, useState } from 'react';
import type { Entorno } from './entorno';

/**
 * Reloj y temporizadores inyectables: los componentes no llaman a `Date` ni a `setTimeout`
 * directamente, así las pruebas controlan el tiempo sin esperar ni usar temporizadores reales.
 */
export interface Reloj {
  ahora(): Date;
  /** Ejecuta `accion` cada `ms`. Devuelve la función que lo detiene. */
  cada(ms: number, accion: () => void): () => void;
  /** Ejecuta `accion` una vez pasados `ms`. Devuelve la función que lo cancela. */
  tras(ms: number, accion: () => void): () => void;
}

export const relojReal: Reloj = {
  ahora: () => new Date(),
  cada: (ms, accion) => {
    const id = setInterval(accion, ms);
    return () => clearInterval(id);
  },
  tras: (ms, accion) => {
    const id = setTimeout(accion, ms);
    return () => clearTimeout(id);
  },
};

/** Cada cuánto se recalcula "hace X min" mientras la app está abierta. */
export const PASO_ANTIGUEDAD_MS = 30_000;

/**
 * Hora actual que se renueva sola, para que la antigüedad mostrada no se congele. Con
 * `entorno`, también se renueva al volver la app a primer plano (el teléfono pudo haber
 * pausado los temporizadores mientras estaba bloqueado).
 */
export function useAhora(
  reloj: Reloj,
  entorno?: Entorno,
  pasoMs: number = PASO_ANTIGUEDAD_MS,
): Date {
  const [ahora, setAhora] = useState(() => reloj.ahora());
  useEffect(() => {
    const renovar = () => setAhora(reloj.ahora());
    renovar();
    const detener = reloj.cada(pasoMs, renovar);
    const dejar = entorno?.escuchar('primer-plano', renovar);
    return () => {
      detener();
      dejar?.();
    };
  }, [reloj, entorno, pasoMs]);
  return ahora;
}
