import { urlHorasDisponibles, type DefinicionCapa } from './capas';
import { ultimoTiempoGibs, ultimoTiempoWms } from './tiempo';

/** Devuelve la hora de la imagen más reciente de una capa, o `null` si el servicio no tiene. */
export type LectorHora = (capa: DefinicionCapa) => Promise<Date | null>;

type Pedir = (url: string) => Promise<Response>;

/** Crea el lector real, que consulta a cada servicio qué horas tiene disponibles. */
export function crearLectorHora(
  pedir: Pedir = (url) => fetch(url),
  ahora: () => Date = () => new Date(),
): LectorHora {
  return async (capa) => {
    const respuesta = await pedir(urlHorasDisponibles(capa, ahora()));
    if (!respuesta.ok) throw new Error(`El servicio respondió ${respuesta.status}`);
    const xml = await respuesta.text();
    return capa.servicio === 'gibs' ? ultimoTiempoGibs(xml) : ultimoTiempoWms(xml, capa.capaWms);
  };
}
