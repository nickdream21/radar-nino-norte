import type { IdCapa } from './capas';

/** Capa lista para dibujar: ya se sabe de qué hora es su imagen. */
export interface CapaEnMapa {
  id: IdCapa;
  url: string;
  atribucion: string;
  zoomMaximo: number;
  opacidad: number;
}

export type MotivoFalloMapa = 'red' | 'no-soportado';

export interface PropsMapa {
  /** Capas encendidas, en el orden en que se apilan (la primera abajo). */
  capas: readonly CapaEnMapa[];
  alFallarCapa: (id: IdCapa) => void;
  alFallarMapa: (motivo: MotivoFalloMapa) => void;
}
