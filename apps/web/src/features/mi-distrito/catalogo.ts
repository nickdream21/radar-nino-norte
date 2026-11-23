import type { CapitalDistrital, Distrito } from '@radar/contratos';
import { FILAS_DISTRITOS } from './distritos.generado';

/**
 * Lo que la web necesita de cada distrito del catálogo (`CatalogoDistritos`) para elegirlo.
 * Se deriva del contrato: si el contrato cambia, esto deja de compilar.
 */
export interface DistritoLista extends Pick<
  Distrito,
  'ubigeo' | 'nombre' | 'provincia' | 'departamento'
> {
  capital: Pick<CapitalDistrital, 'latitud' | 'longitud'>;
}

/** Forma compacta en la que viaja la lista dentro del paquete (ver `distritos.generado.ts`). */
export type FilaDistrito = readonly [
  Distrito['ubigeo'],
  Distrito['nombre'],
  Distrito['provincia'],
  Distrito['departamento'],
  CapitalDistrital['latitud'],
  CapitalDistrital['longitud'],
];

export function desdeFila([
  ubigeo,
  nombre,
  provincia,
  departamento,
  latitud,
  longitud,
]: FilaDistrito): DistritoLista {
  return { ubigeo, nombre, provincia, departamento, capital: { latitud, longitud } };
}

/** Orden alfabético español: "Ñ" después de "N", tildes sin peso propio. */
const colador = new Intl.Collator('es', { sensitivity: 'base' });
export const compararTexto = (a: string, b: string) => colador.compare(a, b);

export interface Catalogo {
  distritos: readonly DistritoLista[];
  porUbigeo(ubigeo: string): DistritoLista | undefined;
  /** Departamentos en orden alfabético. */
  departamentos(): readonly string[];
  /** Provincias de un departamento en orden alfabético. */
  provincias(departamento: string): readonly string[];
  /** Distritos de una provincia en orden alfabético. */
  distritosDe(departamento: string, provincia: string): readonly DistritoLista[];
}

const unicos = (valores: Iterable<string>) => [...new Set(valores)].sort(compararTexto);

export function crearCatalogo(distritos: readonly DistritoLista[]): Catalogo {
  const indice = new Map(distritos.map((d) => [d.ubigeo, d]));
  return {
    distritos,
    porUbigeo: (ubigeo) => indice.get(ubigeo),
    departamentos: () => unicos(distritos.map((d) => d.departamento)),
    provincias: (departamento) =>
      unicos(distritos.filter((d) => d.departamento === departamento).map((d) => d.provincia)),
    distritosDe: (departamento, provincia) =>
      distritos
        .filter((d) => d.departamento === departamento && d.provincia === provincia)
        .sort((a, b) => compararTexto(a.nombre, b.nombre)),
  };
}

/** Los 327 distritos de la zona que cubre la app, incluidos en el paquete inicial. */
export const CATALOGO: Catalogo = crearCatalogo(FILAS_DISTRITOS.map(desdeFila));
