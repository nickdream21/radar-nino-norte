/**
 * Textos de Mi distrito. Definidos por `ux-contenido`: se usan literalmente. Los marcados
 * PROVISIONAL no venían en la especificación y están pendientes de su revisión.
 */
export const TEXTOS_MI_DISTRITO = {
  preparando:
    'Estamos preparando el pronóstico de lluvia por distrito. Mientras tanto, mira los avisos de SENAMHI.',
  cambiarDistrito: 'Cambiar distrito',
  /** PROVISIONAL: volver al distrito guardado sin cambiarlo (la especificación no lo cubre). */
  cancelarCambio: 'Seguir con mi distrito',
};

export const TEXTOS_SELECTOR = {
  titulo: '¿Dónde vives?',
  explicacion:
    'Elige tu distrito para ver la lluvia que se espera ahí. Puedes cambiarlo cuando quieras.',

  // Buscador
  etiquetaBuscador: 'Busca tu distrito',
  sinResultados: 'No encontramos ese distrito. Prueba con otro nombre o búscalo en la lista.',
  /** PROVISIONAL: nombre de la lista de resultados para lectores de pantalla. */
  resultados: 'Resultados de la búsqueda',

  // Ubicación
  usarUbicacion: 'Usar mi ubicación',
  /** PROVISIONAL: mientras el celular busca la posición. */
  buscandoUbicacion: 'Buscando tu ubicación…',
  confirmarSi: 'Sí, es mi distrito',
  confirmarNo: 'No, elegir otro',
  fueraDeZona: 'Parece que estás fuera de la zona que cubre la app. Elige un distrito de la lista.',
  falloUbicacion: 'No pudimos saber tu ubicación. Elige tu distrito de la lista.',

  // Lista en tres pasos
  /** PROVISIONAL: título de la lista alternativa (paso 1, departamentos). */
  tituloLista: 'O elige de la lista',
  /** PROVISIONAL: botón para volver al paso anterior de la lista. */
  volver: 'Volver',
};

/** Resultado de la búsqueda: "Distrito — Provincia, Departamento" (hay nombres repetidos). */
export function textoResultado(d: { nombre: string; provincia: string; departamento: string }) {
  return `${d.nombre} — ${d.provincia}, ${d.departamento}`;
}

/** PROVISIONAL: anuncio para lectores de pantalla con el número de resultados. */
export function textoCuantosResultados(cantidad: number): string {
  return cantidad === 1 ? '1 distrito encontrado.' : `${cantidad} distritos encontrados.`;
}

export function textoConfirmarUbicacion(d: { nombre: string; provincia: string }): string {
  return `¿Estás en ${d.nombre}, ${d.provincia}?`;
}

/** PROVISIONAL: título del paso 2 de la lista. */
export function textoTituloProvincias(departamento: string): string {
  return `Provincias de ${departamento}`;
}

/** PROVISIONAL: título del paso 3 de la lista. */
export function textoTituloDistritos(provincia: string): string {
  return `Distritos de la provincia de ${provincia}`;
}

/** Línea bajo el nombre del distrito elegido. */
export function textoUbicacionDistrito(d: { provincia: string; departamento: string }): string {
  return `${d.provincia}, ${d.departamento}`;
}
