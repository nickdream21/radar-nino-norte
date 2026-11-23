/** Números para el público: coma decimal y signo explícito en las anomalías. */

const MENOS = '−'; // "−": los lectores de pantalla lo leen como "menos", no como guion.

/** Redondea a un decimal sin producir "-0". */
function aUnDecimal(valor: number): number {
  const redondeado = Math.round(valor * 10) / 10;
  return Object.is(redondeado, -0) ? 0 : redondeado;
}

/** `27,5`, `−1,2`. */
export function formatearDecimal(valor: number): string {
  const redondeado = aUnDecimal(valor);
  const texto = Math.abs(redondeado).toFixed(1).replace('.', ',');
  return redondeado < 0 ? `${MENOS}${texto}` : texto;
}

/** `+2,4 °C`, `−0,8 °C`, `0,0 °C`: siempre con signo salvo el cero. */
export function formatearAnomalia(valor: number): string {
  const redondeado = aUnDecimal(valor);
  const signo = redondeado > 0 ? '+' : '';
  return `${signo}${formatearDecimal(redondeado)} °C`;
}

/** Signo de la anomalía tal como se muestra (tras redondear a un decimal). */
export function signoAnomalia(valor: number): 'positiva' | 'negativa' | 'cero' {
  const redondeado = aUnDecimal(valor);
  if (redondeado > 0) return 'positiva';
  if (redondeado < 0) return 'negativa';
  return 'cero';
}
