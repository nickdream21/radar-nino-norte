import type { ReactNode } from 'react';
import { Icono } from './Iconos';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from './textos';

/** Enlace a otra página: icono visible y aviso para lectores de pantalla. */
export function EnlaceExterno({
  href,
  children,
  className = 'enlace',
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className={className}>
      {children}
      <Icono nombre="externo" className="ml-1 inline size-4 align-[-0.125em]" />
      <span className="sr-only"> ({TEXTOS_COMUNES.otraPagina})</span>
    </a>
  );
}

/** Aviso corto de que la app no es una alerta oficial, con enlace a SENAMHI. */
export function AvisoNoOficial() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-white/30 p-3">
      <Icono nombre="info" className="mt-0.5 size-5" />
      <p>
        {TEXTOS_COMUNES.noOficial}{' '}
        <EnlaceExterno href={URL_AVISOS_SENAMHI}>{TEXTOS_COMUNES.verAvisosSenamhi}</EnlaceExterno>
      </p>
    </div>
  );
}
