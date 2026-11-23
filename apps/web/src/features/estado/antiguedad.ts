const MINUTO_MS = 60_000;

/** Describe en lenguaje simple cuánto tiempo pasó entre `desde` y `ahora`. */
export function describirAntiguedad(desde: Date, ahora: Date): string {
  const minutos = Math.floor((ahora.getTime() - desde.getTime()) / MINUTO_MS);
  if (minutos < 1) return 'hace un momento';
  if (minutos < 60) return `hace ${minutos} min`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;

  const dias = Math.floor(horas / 24);
  return dias === 1 ? 'hace 1 día' : `hace ${dias} días`;
}
