// GENERADO por scripts/generar.mjs desde esquemas/*.schema.json. No editar.

/**
 * Estado observado de El Niño para el termómetro de la web.
 */
export interface EstadoNino {
  version_esquema: 1;
  generado_en: string;
  indices_semanales: BloqueIndicesSemanales | null;
  icen: BloqueIcen | null;
  mar_paita: BloqueMarPaita | null;
  enfen: BloqueEnfen | null;
}
/**
 * Índices semanales Niño 1+2 (costa) y Niño 3.4 (Pacífico central).
 */
export interface BloqueIndicesSemanales {
  /**
   * Origen de los datos, para la atribución.
   */
  fuente: string;
  /**
   * Dirección de la fuente.
   */
  url: string;
  /**
   * Fecha del dato más reciente del bloque (UTC).
   */
  fecha_dato: string;
  /**
   * Momento en que el pipeline leyó la fuente con éxito. Si es anterior a `generado_en`, el bloque se conservó de una publicación previa.
   */
  obtenido_en: string;
  nino12: IndiceSemanal;
  nino34: IndiceSemanal;
}
/**
 * Último valor y serie reciente de una región Niño.
 */
export interface IndiceSemanal {
  ultimo: ValorSemanal;
  /**
   * Semanas en orden cronológico; puede tener huecos, nunca valores rellenados.
   *
   * @minItems 1
   * @maxItems 104
   */
  serie: [ValorSemanal, ...ValorSemanal[]];
}
/**
 * Promedio semanal de temperatura superficial del mar en una región Niño.
 */
export interface ValorSemanal {
  /**
   * Día central de la semana, 00:00 UTC.
   */
  fecha: string;
  /**
   * Temperatura del mar en °C.
   */
  temperatura: number;
  /**
   * Anomalía respecto a 1991-2020, en °C.
   */
  anomalia: number;
}
/**
 * Índice Costero El Niño (ICEN) del ENFEN, calculado por el IGP.
 *
 * Solo el valor numérico: la categoría se añadirá cuando se confirmen los umbrales oficiales.
 */
export interface BloqueIcen {
  /**
   * Origen de los datos, para la atribución.
   */
  fuente: string;
  /**
   * Dirección de la fuente.
   */
  url: string;
  /**
   * Fecha del dato más reciente del bloque (UTC).
   */
  fecha_dato: string;
  /**
   * Momento en que el pipeline leyó la fuente con éxito. Si es anterior a `generado_en`, el bloque se conservó de una publicación previa.
   */
  obtenido_en: string;
  ultimo: ValorMensual;
  /**
   * Meses en orden cronológico; puede tener huecos, nunca valores rellenados.
   *
   * @minItems 1
   * @maxItems 36
   */
  serie: [ValorMensual, ...ValorMensual[]];
}
/**
 * Valor del ICEN para un mes.
 */
export interface ValorMensual {
  anio: number;
  mes: number;
  /**
   * Primer día del mes, 00:00 UTC.
   */
  fecha: string;
  /**
   * ICEN en °C.
   */
  valor: number;
}
/**
 * Anomalía diaria de temperatura del mar frente a Paita (Coral Reef Watch, 5 km).
 */
export interface BloqueMarPaita {
  /**
   * Origen de los datos, para la atribución.
   */
  fuente: string;
  /**
   * Dirección de la fuente.
   */
  url: string;
  /**
   * Fecha del dato más reciente del bloque (UTC).
   */
  fecha_dato: string;
  /**
   * Momento en que el pipeline leyó la fuente con éxito. Si es anterior a `generado_en`, el bloque se conservó de una publicación previa.
   */
  obtenido_en: string;
  /**
   * Promedio de las celdas válidas de la caja, en °C.
   */
  anomalia: number;
  caja: Caja;
  celdas_validas: number;
  celdas_totales: number;
}
/**
 * Zona mar adentro promediada.
 */
export interface Caja {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}
/**
 * Estado del sistema de alerta ENFEN. ``fecha_dato`` es la fecha del comunicado.
 */
export interface BloqueEnfen {
  /**
   * Origen de los datos, para la atribución.
   */
  fuente: string;
  /**
   * Dirección de la fuente.
   */
  url: string;
  /**
   * Fecha del dato más reciente del bloque (UTC).
   */
  fecha_dato: string;
  /**
   * Momento en que el pipeline leyó la fuente con éxito. Si es anterior a `generado_en`, el bloque se conservó de una publicación previa.
   */
  obtenido_en: string;
  comunicado: ComunicadoEnfen;
}
/**
 * Último comunicado oficial del ENFEN, mantenido a mano en ``datos-estaticos/enfen.json``.
 */
export interface ComunicadoEnfen {
  /**
   * Estado del sistema de alerta, p. ej. "Alerta de El Niño Costero".
   */
  estado: string;
  /**
   * Número del comunicado, "NN-AAAA".
   */
  numero: string;
  /**
   * Fecha de emisión del comunicado.
   */
  fecha: string;
  /**
   * Dónde leer el comunicado.
   */
  enlace: string;
}

/**
 * Índice que la web lee primero para saber qué hay y qué tan reciente es.
 */
export interface Manifiesto {
  version_esquema: 1;
  generado_en: string;
  version_pipeline: string;
  productos: ProductoPublicado[];
}
/**
 * Un archivo de datos publicado para la web.
 */
export interface ProductoPublicado {
  /**
   * Identificador estable.
   */
  id: string;
  /**
   * Ruta relativa al manifiesto.
   */
  ruta: string;
  /**
   * Origen de los datos, para la atribución.
   */
  fuente: string;
  /**
   * Momento del dato más reciente.
   */
  actualizado_en: string;
  /**
   * Minutos tras los cuales la web debe mostrar el dato como antiguo.
   */
  vigencia_min: number;
}
