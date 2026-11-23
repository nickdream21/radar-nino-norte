// GENERADO por scripts/generar.mjs desde esquemas/*.schema.json. No editar.

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
