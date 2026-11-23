import { EnlaceExterno } from '../../comun/Enlaces';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from '../../comun/textos';
import type { DistritoLista } from './catalogo';
import { TEXTOS_MI_DISTRITO } from './textos';

/**
 * PUNTO DE ENTRADA DEL PRONÓSTICO POR DISTRITO. Es el único lugar de Mi distrito que muestra
 * la lluvia esperada: cuando exista el producto del pipeline, este componente lo leerá con
 * `useProducto` para `distrito.ubigeo` y mostrará sus estados (cargando, sin datos o error,
 * listo y antiguo). Mientras tanto dice con honestidad que aún no está.
 */
// El distrito aún no se usa: la firma queda fijada para el componente del pronóstico.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function PronosticoDistrito(_props: { distrito: DistritoLista }) {
  return (
    <p>
      {TEXTOS_MI_DISTRITO.preparando}{' '}
      <EnlaceExterno href={URL_AVISOS_SENAMHI}>{TEXTOS_COMUNES.verAvisosSenamhi}</EnlaceExterno>
    </p>
  );
}
