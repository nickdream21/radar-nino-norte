/**
 * Funciones puras para saber de qué hora es la imagen de cada capa y cómo decirlo.
 */

/**
 * Último instante de una lista de tiempos ISO 8601 como la que publican GIBS y los WMS:
 * valores sueltos (`2026-11-23T14:00:00Z`) o intervalos (`inicio/fin/periodo`),
 * separados por comas. Devuelve `null` si no hay ninguno válido.
 */
export function ultimoInstante(valores: string): Date | null {
  let ultimo: Date | null = null;
  for (const valor of valores.split(',')) {
    const partes = valor.trim().split('/');
    const candidato = partes.length >= 2 ? partes[1] : partes[0];
    if (!candidato) continue;
    const tiempo = new Date(candidato);
    if (Number.isNaN(tiempo.getTime())) continue;
    if (!ultimo || tiempo > ultimo) ultimo = tiempo;
  }
  return ultimo;
}

function parsearXml(xml: string): Document | null {
  const documento = new DOMParser().parseFromString(xml, 'application/xml');
  return documento.getElementsByTagName('parsererror').length > 0 ? null : documento;
}

/** Última hora disponible según la respuesta "DescribeDomains" de GIBS. */
export function ultimoTiempoGibs(xml: string): Date | null {
  const documento = parsearXml(xml);
  if (!documento) return null;
  const dominios = documento.getElementsByTagNameNS('*', 'Domain');
  let ultimo: Date | null = null;
  for (const dominio of Array.from(dominios)) {
    const tiempo = ultimoInstante(dominio.textContent);
    if (tiempo && (!ultimo || tiempo > ultimo)) ultimo = tiempo;
  }
  return ultimo;
}

/** Última hora disponible de una capa según el GetCapabilities de un WMS 1.3.0. */
export function ultimoTiempoWms(xml: string, capaWms: string): Date | null {
  const documento = parsearXml(xml);
  if (!documento) return null;
  for (const capa of Array.from(documento.getElementsByTagNameNS('*', 'Layer'))) {
    const nombre = Array.from(capa.children).find((hijo) => hijo.localName === 'Name');
    if (nombre?.textContent.trim() !== capaWms) continue;
    const dimension = Array.from(capa.children).find(
      (hijo) => hijo.localName === 'Dimension' && hijo.getAttribute('name') === 'time',
    );
    return dimension ? ultimoInstante(dimension.textContent) : null;
  }
  return null;
}

// Perú no cambia de hora en verano desde 1994: UTC−5 todo el año.
const DESFASE_PERU_MS = -5 * 60 * 60 * 1000;
const DIA_MS = 24 * 60 * 60 * 1000;
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** Fecha y hora "de pared" en Perú, leídas con los métodos UTC. */
function enPeru(tiempo: Date): Date {
  return new Date(tiempo.getTime() + DESFASE_PERU_MS);
}

function diaPeru(tiempo: Date): number {
  return Math.floor(enPeru(tiempo).getTime() / DIA_MS);
}

/** `8:50 a. m.`, `12:05 p. m.` en hora de Perú. */
export function formatearHoraPeru(tiempo: Date): string {
  const local = enPeru(tiempo);
  const horas = local.getUTCHours();
  const minutos = String(local.getUTCMinutes()).padStart(2, '0');
  const horas12 = horas % 12 === 0 ? 12 : horas % 12;
  return `${horas12}:${minutos} ${horas < 12 ? 'a. m.' : 'p. m.'}`;
}

/** Día de la imagen respecto de hoy en Perú: `null` si es hoy, `ayer` o `22 nov`. */
export function describirDiaPeru(tiempo: Date, ahora: Date): string | null {
  const diferencia = diaPeru(ahora) - diaPeru(tiempo);
  if (diferencia === 0) return null;
  if (diferencia === 1) return 'ayer';
  const local = enPeru(tiempo);
  return `${local.getUTCDate()} ${MESES[local.getUTCMonth()] ?? ''}`.trim();
}

/** Indica si la imagen superó el tiempo tras el cual ya no se considera reciente. */
export function esAntigua(tiempo: Date, ahora: Date, antiguaTrasMin: number): boolean {
  return ahora.getTime() - tiempo.getTime() > antiguaTrasMin * 60_000;
}
