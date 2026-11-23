// GENERADO por scripts/generar.mjs desde esquemas/*.schema.json. No editar.

/**
 * Todos los distritos de los cinco departamentos, ordenados por ubigeo.
 */
export interface CatalogoDistritos {
  version_esquema: 1;
  generado_en: string;
  /**
   * @minItems 1
   */
  fuentes: [FuenteCatalogo, ...FuenteCatalogo[]];
  /**
   * @minItems 1
   */
  distritos: [Distrito, ...Distrito[]];
}
/**
 * Procedencia de uno o varios campos del catálogo.
 */
export interface FuenteCatalogo {
  /**
   * Campos que aporta esta fuente.
   */
  campos: string;
  nombre: string;
  url: string;
  licencia: string;
  atribucion: string;
  descargado_en: string;
}
/**
 * Un distrito con su capital y su zona pluviométrica.
 */
export interface Distrito {
  /**
   * Código INEI de 6 dígitos.
   */
  ubigeo: string;
  nombre: string;
  provincia: string;
  departamento: string;
  capital: CapitalDistrital;
  vertiente: 'pacifico' | 'atlantico';
  /**
   * Unidad hidrográfica (ANA) en la que está la capital.
   */
  cuenca: string;
  /**
   * De la capital a la línea de costa.
   */
  distancia_costa_km: number;
  /**
   * Calculada con la regla de zonas, nunca escrita a mano.
   */
  zona: 'A' | 'B' | 'C' | 'D';
  /**
   * Motivos por los que la zona es dudosa o fronteriza y debe revisarla el meteorólogo. Vacía si la regla se aplica sin ambigüedad.
   */
  revisar: string[];
}
/**
 * Capital del distrito: el punto que representa al distrito en los pronósticos.
 */
export interface CapitalDistrital {
  nombre: string;
  /**
   * Grados decimales, WGS 84.
   */
  latitud: number;
  /**
   * Grados decimales, WGS 84.
   */
  longitud: number;
  /**
   * Metros sobre el nivel del mar, del modelo de elevación.
   */
  altitud_m: number;
  fuente_ubicacion: 'inei-ccpp' | 'geonames';
}

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
 * Semáforo de lluvia por distrito, sin verificar todavía.
 */
export interface LluviaDistritos {
  version_esquema: 1;
  generado_en: string;
  verificacion: 'sin_verificar';
  metodo: MetodoLluvia;
  /**
   * @minItems 1
   */
  corridas: [CorridaUsada, ...CorridaUsada[]];
  /**
   * @minItems 3
   * @maxItems 3
   */
  dias: [DiaPronostico, DiaPronostico, DiaPronostico];
  tendencia: PeriodoTendencia;
  celdas: CeldaModelo[];
  /**
   * @minItems 1
   */
  distritos: [DistritoLluvia, ...DistritoLluvia[]];
}
/**
 * Criterios con que se calculó el producto, para que viajen con los datos.
 */
export interface MetodoLluvia {
  modelo: 'm1-v1';
  /**
   * Pesos nominales de la mezcla.
   */
  pesos: {
    [k: string]: number;
  };
  /**
   * Lluvia diaria de 12 a 12 UTC; provisionales hasta contrastarlos.
   */
  umbrales_mm: {
    [k: string]: UmbralesZona;
  };
  niveles: CriteriosNiveles;
  tope_tendencia: 1 | 2 | 3 | 4;
  /**
   * Distancia máxima entre la corrida de un sistema y la ECMWF más reciente.
   */
  desfase_maximo_h: number;
  altitud_sierra_m: number;
  /**
   * Capital por debajo de altitud_sierra_m: diferencia máxima con la celda.
   */
  diferencia_altitud_costa_m: number;
  /**
   * Capital a altitud_sierra_m o más: diferencia máxima con la celda.
   */
  diferencia_altitud_sierra_m: number;
}
export interface UmbralesZona {
  t1_mm: number;
  t2_mm: number;
  t3_mm: number;
}
/**
 * Porcentajes mínimos (comparados con ``>=``) que activan cada nivel; gana el más alto.
 */
export interface CriteriosNiveles {
  amarillo_t1: number;
  naranja_t2: number;
  naranja_t3: number;
  rojo_t3: number;
  rojo_t2: number;
}
export interface CorridaUsada {
  sistema: 'ecmwf_ifs' | 'ecmwf_aifs' | 'ncep_gefs';
  /**
   * Identificador del modelo en Open-Meteo.
   */
  modelo: string;
  inicializacion: string;
  miembros: number;
  /**
   * Peso renormalizado entre las corridas usadas.
   */
  peso: number;
}
/**
 * Día pluviométrico: de las 7 a. m. a las 7 a. m. del día siguiente en Perú.
 */
export interface DiaPronostico {
  inicio: string;
  fin: string;
  /**
   * Sistemas con dato ese día.
   */
  sistemas: ('ecmwf_ifs' | 'ecmwf_aifs' | 'ncep_gefs')[];
}
/**
 * Días 4 a 7: un único nivel, el más alto, con tope y confianza baja.
 */
export interface PeriodoTendencia {
  inicio: string;
  fin: string;
  confianza: 'baja';
}
/**
 * Celda de 0.25° que Open-Meteo usó para el distrito (la del sistema ECMWF ancla).
 */
export interface CeldaModelo {
  latitud: number;
  longitud: number;
  /**
   * Altitud media de la celda en el modelo.
   */
  altitud_m: number | null;
}
export interface DistritoLluvia {
  ubigeo: string;
  zona: 'A' | 'B' | 'C' | 'D';
  /**
   * Índice en ``celdas``; None si no hubo dato.
   */
  celda: number | null;
  /**
   * La celda es mar o su altitud difiere demasiado de la capital.
   */
  mal_representado: boolean;
  /**
   * @minItems 3
   * @maxItems 3
   */
  dias: [DiaDistritoLluvia, DiaDistritoLluvia, DiaDistritoLluvia];
  tendencia: (1 | 2 | 3) | null;
}
export interface DiaDistritoLluvia {
  /**
   * None: ningún sistema ECMWF tuvo dato.
   */
  nivel: (1 | 2 | 3 | 4) | null;
  /**
   * P(≥T1), P(≥T2) y P(≥T3) de la zona del distrito, en %.
   */
  probabilidades: [number, number, number] | null;
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
