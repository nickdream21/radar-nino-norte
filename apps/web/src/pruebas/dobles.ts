import type { Almacen } from '../features/estado/almacen';
import type { Entorno, EventoEntorno } from '../comun/entorno';
import type { Reloj } from '../comun/reloj';

interface Temporizador {
  id: number;
  vence: number;
  cadaMs: number | null;
  accion: () => void;
}

/** Reloj manual: el tiempo solo avanza con `avanzar`, que dispara los temporizadores vencidos. */
export function crearRelojFalso(inicio: Date) {
  let ahora = inicio.getTime();
  let siguienteId = 0;
  let temporizadores: Temporizador[] = [];

  const programar = (ms: number, accion: () => void, repetir: boolean) => {
    const id = ++siguienteId;
    temporizadores.push({ id, vence: ahora + ms, cadaMs: repetir ? ms : null, accion });
    return () => {
      temporizadores = temporizadores.filter((t) => t.id !== id);
    };
  };

  const reloj: Reloj = {
    ahora: () => new Date(ahora),
    cada: (ms, accion) => programar(ms, accion, true),
    tras: (ms, accion) => programar(ms, accion, false),
  };

  function avanzar(ms: number) {
    const destino = ahora + ms;
    for (;;) {
      const proximo = temporizadores
        .filter((t) => t.vence <= destino)
        .sort((a, b) => a.vence - b.vence || a.id - b.id)[0];
      if (!proximo) break;
      ahora = proximo.vence;
      if (proximo.cadaMs === null) {
        temporizadores = temporizadores.filter((t) => t.id !== proximo.id);
      } else {
        proximo.vence += proximo.cadaMs;
      }
      proximo.accion();
    }
    ahora = destino;
  }

  return { reloj, avanzar, pendientes: () => temporizadores.length };
}

/** Entorno de red controlable: `cambiarRed(false)` simula cortar la conexión. */
export function crearEntornoFalso(enLinea = true) {
  let conectado = enLinea;
  const oyentes = new Map<EventoEntorno, Set<() => void>>();

  const entorno: Entorno = {
    enLinea: () => conectado,
    escuchar: (evento, accion) => {
      const conjunto = oyentes.get(evento) ?? new Set();
      conjunto.add(accion);
      oyentes.set(evento, conjunto);
      return () => conjunto.delete(accion);
    },
  };

  const emitir = (evento: EventoEntorno) => {
    for (const accion of oyentes.get(evento) ?? []) accion();
  };

  return {
    entorno,
    cambiarRed(valor: boolean) {
      conectado = valor;
      emitir(valor ? 'en-linea' : 'fuera-de-linea');
    },
    volverAPrimerPlano: () => emitir('primer-plano'),
  };
}

/** Almacén en memoria. */
export function crearAlmacenFalso(inicial: Record<string, string> = {}): Almacen & {
  contenido: Map<string, string>;
} {
  const contenido = new Map(Object.entries(inicial));
  return {
    contenido,
    leer: (clave) => contenido.get(clave) ?? null,
    guardar: (clave, valor) => {
      contenido.set(clave, valor);
    },
  };
}
