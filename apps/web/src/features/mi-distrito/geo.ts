import type { DistritoLista } from './catalogo';

export interface Coordenadas {
  latitud: number;
  longitud: number;
}

/** Más lejos que esto de toda capital distrital, la ubicación queda fuera de la zona de la app. */
export const DISTANCIA_MAXIMA_KM = 60;

const RADIO_TIERRA_KM = 6371.0088;
const radianes = (grados: number) => (grados * Math.PI) / 180;

/** Distancia sobre la superficie terrestre (fórmula del haversine), en km. */
export function distanciaKm(a: Coordenadas, b: Coordenadas): number {
  const dLat = radianes(b.latitud - a.latitud);
  const dLon = radianes(b.longitud - a.longitud);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(radianes(a.latitud)) * Math.cos(radianes(b.latitud)) * Math.sin(dLon / 2) ** 2;
  return 2 * RADIO_TIERRA_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type Cercania =
  { tipo: 'dentro'; distrito: DistritoLista; distanciaKm: number } | { tipo: 'fuera' };

/**
 * Distrito cuya capital está más cerca de `punto`. No es el distrito que contiene el punto
 * (la app no tiene los límites distritales): por eso siempre se pide confirmar.
 */
export function distritoMasCercano(
  distritos: readonly DistritoLista[],
  punto: Coordenadas,
  maximoKm: number = DISTANCIA_MAXIMA_KM,
): Cercania {
  let mejor: DistritoLista | null = null;
  let mejorKm = Infinity;
  for (const distrito of distritos) {
    const km = distanciaKm(punto, distrito.capital);
    if (km < mejorKm) {
      mejor = distrito;
      mejorKm = km;
    }
  }
  return mejor && mejorKm <= maximoKm
    ? { tipo: 'dentro', distrito: mejor, distanciaKm: mejorKm }
    : { tipo: 'fuera' };
}
