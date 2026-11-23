import { useEffect, useRef } from 'react';

/** Identificador del `h1` de cada pantalla; recibe el foco al cambiar de sección o de paso. */
export const ID_TITULO = 'titulo-seccion';

/**
 * Lleva el foco al `h1` cuando `clave` cambia (un paso nuevo dentro de una sección), para que
 * los lectores de pantalla anuncien dónde se está. No lo mueve en el primer render: de eso se
 * encarga `App` al cambiar de sección.
 */
export function useEnfocarTituloAlCambiar(clave: string) {
  const anterior = useRef(clave);
  useEffect(() => {
    if (anterior.current === clave) return;
    anterior.current = clave;
    document.getElementById(ID_TITULO)?.focus();
  }, [clave]);
}
