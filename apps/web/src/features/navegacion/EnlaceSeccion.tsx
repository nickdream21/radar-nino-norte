import type { MouseEvent, ReactNode } from 'react';
import { SECCIONES, navegar, type IdSeccion } from './secciones';

interface Props {
  a: IdSeccion;
  children: ReactNode;
  className?: string;
  'aria-current'?: 'page';
}

/**
 * Enlace a una sección de la app. Es un `<a>` de verdad (se puede abrir en otra pestaña), pero
 * un toque normal pasa por `navegar` para que el botón Atrás vuelva a Mi distrito.
 */
export function EnlaceSeccion({ a, children, className = 'enlace', ...resto }: Props) {
  const alPulsar = (evento: MouseEvent<HTMLAnchorElement>) => {
    if (evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey)
      return;
    evento.preventDefault();
    navegar(a);
  };
  return (
    <a href={SECCIONES[a].ruta} onClick={alPulsar} className={className} {...resto}>
      {children}
    </a>
  );
}
