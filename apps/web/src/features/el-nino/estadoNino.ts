import type { EstadoNino } from '@radar/contratos';
import { consultarProducto, type Resultado } from '../estado/manifiesto';

export const ID_ESTADO_NINO = 'estado-nino';

/** Pasado este tiempo desde el comunicado, se advierte que puede haber uno más reciente. */
export const DIAS_COMUNICADO_RECIENTE = 21;

/** Campos que la pantalla usa de cada bloque, con su tipo. */
const CAMPOS_USADOS = {
  indices_semanales: {
    fecha_dato: 'fecha',
    'nino12.ultimo.fecha': 'fecha',
    'nino12.ultimo.temperatura': 'number',
    'nino12.ultimo.anomalia': 'number',
  },
  icen: {
    fecha_dato: 'fecha',
    'ultimo.anio': 'number',
    'ultimo.mes': 'number',
    'ultimo.valor': 'number',
  },
  mar_paita: { fecha_dato: 'fecha', anomalia: 'number' },
  enfen: {
    fecha_dato: 'fecha',
    'comunicado.estado': 'string',
    'comunicado.fecha': 'fecha',
    'comunicado.enlace': 'string',
  },
} as const;

function leerRuta(objeto: unknown, ruta: string): unknown {
  let actual = objeto;
  for (const parte of ruta.split('.')) {
    if (typeof actual !== 'object' || actual === null) return undefined;
    actual = (actual as Record<string, unknown>)[parte];
  }
  return actual;
}

function cumpleTipo(valor: unknown, tipo: 'fecha' | 'number' | 'string'): boolean {
  if (tipo === 'number') return typeof valor === 'number' && Number.isFinite(valor);
  if (tipo === 'string') return typeof valor === 'string';
  return typeof valor === 'string' && !Number.isNaN(new Date(valor).getTime());
}

/**
 * Validación mínima en ejecución (ADR 0005): versión y los campos que la pantalla usa. La
 * validación completa la hace el pipeline al escribir. Cada bloque puede venir `null`.
 */
export function esEstadoNino(datos: unknown): datos is EstadoNino {
  if (typeof datos !== 'object' || datos === null) return false;
  const candidato = datos as Record<string, unknown>;
  if (candidato.version_esquema !== 1 || typeof candidato.generado_en !== 'string') return false;
  return Object.entries(CAMPOS_USADOS).every(([bloque, campos]) => {
    const valor = candidato[bloque];
    if (valor === null) return true;
    return Object.entries(campos).every(([ruta, tipo]) => cumpleTipo(leerRuta(valor, ruta), tipo));
  });
}

export function leerEstadoNino(): Promise<Resultado<EstadoNino>> {
  return consultarProducto(ID_ESTADO_NINO, esEstadoNino);
}

export function comunicadoEsAntiguo(fecha: Date, ahora: Date): boolean {
  return ahora.getTime() - fecha.getTime() > DIAS_COMUNICADO_RECIENTE * 24 * 60 * 60_000;
}
