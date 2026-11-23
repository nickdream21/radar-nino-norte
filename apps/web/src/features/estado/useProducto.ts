import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import { entornoNavegador, type Entorno } from '../../comun/entorno';
import { relojReal, useAhora, type Reloj } from '../../comun/reloj';
import { almacenNavegador, type Almacen } from './almacen';
import {
  ESPERA_LENTA_MS,
  calcularVista,
  estadoInicial,
  reducir,
  type EstadoProducto,
  type Vista,
} from './estadoProducto';
import { esProductoPublicado, type Copia, type Resultado, type Validador } from './manifiesto';

/** Con la app abierta, se vuelve a consultar cada tanto aunque no pase nada más. */
const REFRESCO_MS = 30 * 60_000;

export interface Dependencias {
  reloj?: Reloj;
  entorno?: Entorno;
  almacen?: Almacen;
}

interface Opciones<T> extends Dependencias {
  /** Identificador del producto en el manifiesto; también nombra su copia guardada. */
  id: string;
  leer: () => Promise<Resultado<T>>;
  validar: Validador<T>;
}

export interface ProductoEnPantalla<T> {
  vista: Vista<T>;
  ahora: Date;
  reintentar: () => void;
}

const claveAlmacen = (id: string) => `radar:producto:${id}`;

function leerCopiaGuardada<T>(
  almacen: Almacen,
  id: string,
  validar: Validador<T>,
): Copia<T> | null {
  const texto = almacen.leer(claveAlmacen(id));
  if (!texto) return null;
  try {
    const guardado: unknown = JSON.parse(texto);
    if (typeof guardado !== 'object' || guardado === null) return null;
    const { producto, datos } = guardado as Record<string, unknown>;
    return esProductoPublicado(producto) && validar(datos) ? { producto, datos } : null;
  } catch {
    return null;
  }
}

/**
 * Estado de un producto del manifiesto: muestra al instante la copia guardada, la renueva
 * al abrir, al volver la red, al volver la app a primer plano y cada media hora, y recalcula
 * su antigüedad sin quedarse congelada.
 */
export function useProducto<T>({
  id,
  leer,
  validar,
  reloj = relojReal,
  entorno = entornoNavegador,
  almacen = almacenNavegador,
}: Opciones<T>): ProductoEnPantalla<T> {
  const [estado, despachar] = useReducer(reducir<T>, undefined, (): EstadoProducto<T> =>
    estadoInicial(leerCopiaGuardada(almacen, id, validar), entorno.enLinea()),
  );
  const ahora = useAhora(reloj, entorno);
  // Número de la última consulta: descarta respuestas que llegan tarde.
  const ultima = useRef(0);

  const consultar = useCallback(() => {
    const numero = ++ultima.current;
    const vigente = () => ultima.current === numero;
    if (!entorno.enLinea()) {
      despachar({ tipo: 'fuera-de-linea' });
      return;
    }
    despachar({ tipo: 'consultando' });
    const cancelarEspera = reloj.tras(ESPERA_LENTA_MS, () => {
      if (vigente()) despachar({ tipo: 'lenta' });
    });
    leer().then(
      (resultado) => {
        cancelarEspera();
        if (!vigente()) return;
        if (resultado.tipo === 'listo') {
          almacen.guardar(claveAlmacen(id), JSON.stringify(resultado.copia));
        }
        despachar({ tipo: 'resultado', resultado });
      },
      () => {
        cancelarEspera();
        if (vigente()) despachar({ tipo: 'resultado', resultado: { tipo: 'error' } });
      },
    );
  }, [id, leer, reloj, entorno, almacen]);

  useEffect(() => {
    // Invalidar la consulta en curso: su respuesta ya no debe aplicarse.
    const descartarEnCurso = () => ultima.current++;
    consultar();
    const dejar = [
      entorno.escuchar('en-linea', consultar),
      entorno.escuchar('primer-plano', consultar),
      entorno.escuchar('fuera-de-linea', () => {
        descartarEnCurso();
        despachar({ tipo: 'fuera-de-linea' });
      }),
      reloj.cada(REFRESCO_MS, consultar),
    ];
    return () => {
      descartarEnCurso();
      for (const deja of dejar) deja();
    };
  }, [consultar, entorno, reloj]);

  const vista = useMemo(() => calcularVista(estado, ahora), [estado, ahora]);
  return { vista, ahora, reintentar: consultar };
}
