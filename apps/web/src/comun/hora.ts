/**
 * Fechas y horas para el público, siempre en hora de Lima y nunca en la del teléfono.
 * Funciones puras: reciben `ahora` en vez de leer el reloj.
 */

// Perú no cambia de hora en verano desde 1994: UTC−5 todo el año.
const DESFASE_LIMA_MS = -5 * 60 * 60 * 1000;
const MINUTO_MS = 60_000;
const DIA_MS = 24 * 60 * MINUTO_MS;

/** Margen para no tratar como "futuro" un desfase mínimo entre relojes. */
const TOLERANCIA_FUTURO_MS = MINUTO_MS;

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];
const MESES_CORTOS = MESES.map((mes) => mes.slice(0, 3));

/** Fecha y hora "de pared" en Lima, leídas con los métodos UTC. */
function enLima(tiempo: Date): Date {
  return new Date(tiempo.getTime() + DESFASE_LIMA_MS);
}

function diaLima(tiempo: Date): number {
  return Math.floor(enLima(tiempo).getTime() / DIA_MS);
}

function esFuturo(tiempo: Date, ahora: Date): boolean {
  return tiempo.getTime() - ahora.getTime() > TOLERANCIA_FUTURO_MS;
}

/** `8:50 a. m.`, `12:05 p. m.` en hora de Lima. */
export function formatearHoraLima(tiempo: Date): string {
  const local = enLima(tiempo);
  const horas = local.getUTCHours();
  const minutos = String(local.getUTCMinutes()).padStart(2, '0');
  const horas12 = horas % 12 === 0 ? 12 : horas % 12;
  return `${horas12}:${minutos} ${horas < 12 ? 'a. m.' : 'p. m.'}`;
}

/** "la 1:05 p. m." pero "las 2:05 p. m.". */
export function conArticulo(hora: string): string {
  return `${hora.startsWith('1:') ? 'la' : 'las'} ${hora}`;
}

/** Día corto respecto de hoy en Lima: `null` si es hoy, `ayer` o `22 nov`. Lo usa el mapa. */
export function describirDiaCorto(tiempo: Date, ahora: Date): string | null {
  const diferencia = diaLima(ahora) - diaLima(tiempo);
  if (diferencia === 0) return null;
  if (diferencia === 1) return 'ayer';
  const local = enLima(tiempo);
  return `${local.getUTCDate()} ${MESES_CORTOS[local.getUTCMonth()] ?? ''}`.trim();
}

/**
 * Fecha de calendario: `13 de noviembre`, con el año solo si no es el de `ahora`.
 * `zona: 'utc'` lee el día UTC: sirve para fechas que la fuente da a las 00:00 UTC como
 * día de calendario (pasarlas a Lima las movería al día anterior).
 */
export function formatearFecha(tiempo: Date, ahora: Date, zona: 'lima' | 'utc' = 'lima'): string {
  const local = zona === 'lima' ? enLima(tiempo) : tiempo;
  const anio = local.getUTCFullYear();
  const base = `${local.getUTCDate()} de ${MESES[local.getUTCMonth()] ?? ''}`;
  return anio === enLima(ahora).getUTCFullYear() ? base : `${base} de ${anio}`;
}

/** `septiembre de 2026`. `mes` va de 1 a 12. */
export function formatearMes(anio: number, mes: number): string {
  return `${MESES[mes - 1] ?? ''} de ${anio}`;
}

type Dia = { tipo: 'hoy' } | { tipo: 'ayer' } | { tipo: 'fecha'; texto: string };

/**
 * Día del dato respecto de hoy en Lima. Una fecha futura (reloj del teléfono atrasado)
 * nunca se describe como "hoy": se da la fecha completa.
 */
function diaRelativo(tiempo: Date, ahora: Date): Dia {
  if (!esFuturo(tiempo, ahora)) {
    const diferencia = diaLima(ahora) - diaLima(tiempo);
    if (diferencia === 0) return { tipo: 'hoy' };
    if (diferencia === 1) return { tipo: 'ayer' };
  }
  return { tipo: 'fecha', texto: formatearFecha(tiempo, ahora) };
}

/** `hoy a las 6:10 a. m.`, `ayer a la 1:05 p. m.`, `el 20 de noviembre a las 3:00 p. m.`. */
export function describirMomento(tiempo: Date, ahora: Date): string {
  const dia = diaRelativo(tiempo, ahora);
  const hora = conArticulo(formatearHoraLima(tiempo));
  if (dia.tipo === 'fecha') return `el ${dia.texto} a ${hora}`;
  return `${dia.tipo} a ${hora}`;
}

/** Igual que `describirMomento`, precedido de "de": `de ayer a las…`, `del 20 de noviembre a las…`. */
export function describirMomentoConDe(tiempo: Date, ahora: Date): string {
  const momento = describirMomento(tiempo, ahora);
  return momento.startsWith('el ') ? `d${momento}` : `de ${momento}`;
}

/**
 * Cuánto tiempo pasó, en lenguaje simple. `null` si la fecha está en el futuro: con el reloj
 * del teléfono atrasado no se puede decir cuánto pasó, y no se finge que es reciente.
 */
export function describirAntiguedad(desde: Date, ahora: Date): string | null {
  if (esFuturo(desde, ahora)) return null;
  const minutos = Math.floor((ahora.getTime() - desde.getTime()) / MINUTO_MS);
  if (minutos < 1) return 'hace un momento';
  if (minutos < 60) return `hace ${minutos} min`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;

  const dias = Math.floor(horas / 24);
  return dias === 1 ? 'hace 1 día' : `hace ${dias} días`;
}

/**
 * Antigüedad para mostrar junto a un dato: relativa, y además absoluta si tiene más de una
 * hora (`hace 3 h, hoy a las 6:10 a. m.`). Si la fecha está en el futuro, solo la absoluta.
 */
export function describirAntiguedadCompleta(desde: Date, ahora: Date): string {
  const relativa = describirAntiguedad(desde, ahora);
  if (relativa === null) return describirMomento(desde, ahora);
  if (ahora.getTime() - desde.getTime() <= 60 * MINUTO_MS) return relativa;
  return `${relativa}, ${describirMomento(desde, ahora)}`;
}

/** Indica si pasaron más de `minutos` desde `tiempo`. Una fecha futura nunca es antigua. */
export function superoMinutos(tiempo: Date, ahora: Date, minutos: number): boolean {
  return ahora.getTime() - tiempo.getTime() > minutos * MINUTO_MS;
}
