/**
 * Lógica pura de los estados de un producto: qué se muestra según lo que hay guardado, cómo
 * terminó la última consulta y la hora actual. Sin React ni red, para probarla directamente.
 */
import { superoMinutos } from '../../comun/hora';
import type { Copia, Resultado } from './manifiesto';

/** Más allá de este tiempo de espera se ofrece reintentar. */
export const ESPERA_LENTA_MS = 8_000;

export type Consulta = 'cargando' | 'lenta' | 'listo' | 'sin-datos' | 'sin-conexion' | 'error';

export interface EstadoProducto<T> {
  /** Último dato válido: el guardado en el teléfono o el que acaba de llegar. */
  copia: Copia<T> | null;
  consulta: Consulta;
}

export type Accion<T> =
  | { tipo: 'consultando' }
  | { tipo: 'lenta' }
  | { tipo: 'fuera-de-linea' }
  | { tipo: 'resultado'; resultado: Resultado<T> };

export function estadoInicial<T>(copia: Copia<T> | null, enLinea: boolean): EstadoProducto<T> {
  return { copia, consulta: enLinea ? 'cargando' : 'sin-conexion' };
}

export function reducir<T>(estado: EstadoProducto<T>, accion: Accion<T>): EstadoProducto<T> {
  switch (accion.tipo) {
    case 'consultando':
      return { ...estado, consulta: 'cargando' };
    case 'lenta':
      return estado.consulta === 'cargando' ? { ...estado, consulta: 'lenta' } : estado;
    case 'fuera-de-linea':
      return { ...estado, consulta: 'sin-conexion' };
    case 'resultado': {
      const { resultado } = accion;
      if (resultado.tipo === 'listo') return { copia: resultado.copia, consulta: 'listo' };
      // Un fallo nunca borra el último dato válido: seguirá a la vista con su hora.
      return { ...estado, consulta: resultado.tipo };
    }
  }
}

/** Franja de estado que se muestra antes del contenido, en este orden. */
export type Franja =
  | { tipo: 'cargando' }
  | { tipo: 'lenta' }
  | { tipo: 'sin-datos' }
  | { tipo: 'sin-conexion-con-dato'; momento: Date }
  | { tipo: 'sin-conexion-sin-dato' }
  | { tipo: 'error' }
  | { tipo: 'antiguo'; momento: Date };

export interface Vista<T> {
  franjas: Franja[];
  /** Dato que se puede mostrar; `null` si no hay ninguno (nunca un valor por defecto). */
  copia: Copia<T> | null;
  /** Hora del dato mostrado. */
  momento: Date | null;
}

export function momentoDe<T>(copia: Copia<T>): Date {
  return new Date(copia.producto.actualizado_en);
}

/** Un dato es antiguo cuando superó la vigencia que declara su producto en el manifiesto. */
export function esAntiguo<T>(copia: Copia<T>, ahora: Date): boolean {
  return superoMinutos(momentoDe(copia), ahora, copia.producto.vigencia_min);
}

export function calcularVista<T>(estado: EstadoProducto<T>, ahora: Date): Vista<T> {
  const { copia, consulta } = estado;
  const momento = copia ? momentoDe(copia) : null;
  const franjas: Franja[] = [];

  switch (consulta) {
    case 'cargando':
      franjas.push({ tipo: 'cargando' });
      break;
    case 'lenta':
      franjas.push({ tipo: 'lenta' });
      break;
    case 'sin-datos':
      // Si hay un dato guardado se sigue mostrando, marcado como antiguo cuando corresponda.
      if (!copia) franjas.push({ tipo: 'sin-datos' });
      break;
    case 'sin-conexion':
      franjas.push(
        momento ? { tipo: 'sin-conexion-con-dato', momento } : { tipo: 'sin-conexion-sin-dato' },
      );
      break;
    case 'error':
      franjas.push({ tipo: 'error' });
      break;
    case 'listo':
      break;
  }

  if (copia && momento && esAntiguo(copia, ahora)) franjas.push({ tipo: 'antiguo', momento });

  return { franjas, copia, momento };
}

/** Franjas que llevan botón "Reintentar". */
export function admiteReintento(franja: Franja): boolean {
  return (
    franja.tipo === 'lenta' || franja.tipo === 'sin-conexion-sin-dato' || franja.tipo === 'error'
  );
}
