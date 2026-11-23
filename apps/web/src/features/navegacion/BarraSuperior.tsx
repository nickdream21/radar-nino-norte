import { Icono } from '../../comun/Iconos';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from '../../comun/textos';

/** Barra superior delgada: nombre de la app y acceso directo a los avisos oficiales. */
export function BarraSuperior() {
  return (
    <header className="bg-superficie border-b border-white/20 pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-xl flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 py-1">
        <p className="font-bold">{TEXTOS_COMUNES.nombreApp}</p>
        <a
          href={URL_AVISOS_SENAMHI}
          target="_blank"
          rel="noreferrer"
          className="boton boton-secundario"
        >
          {TEXTOS_COMUNES.avisosSenamhi}
          <Icono nombre="externo" className="size-4" />
          <span className="sr-only"> ({TEXTOS_COMUNES.otraPagina})</span>
        </a>
      </div>
    </header>
  );
}
