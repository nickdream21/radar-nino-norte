import { SECCIONES, type IdSeccion } from './secciones';

const ICONOS: Record<IdSeccion, string> = {
  // Casa
  inicio: 'M10 2 1 9.5V18h6v-5h6v5h6V9.5L10 2Z',
  // Mapa plegado
  mapa: 'M1 4.5 7 2l6 2.5L19 2v13.5L13 18l-6-2.5L1 18V4.5Zm6 0v9.4l6 2.5V7L7 4.5Z',
};

/** Barra inferior, al alcance del pulgar con el celular en una mano. */
export function BarraNavegacion({ activa }: { activa: IdSeccion }) {
  return (
    <nav aria-label="Secciones" className="bg-superficie border-t border-white/10">
      <ul className="mx-auto flex max-w-xl">
        {SECCIONES.map(({ id, nombre }) => {
          const actual = id === activa;
          return (
            <li key={id} className="flex-1">
              <a
                href={`#${id}`}
                aria-current={actual ? 'page' : undefined}
                className={`flex min-h-14 flex-col items-center justify-center gap-0.5 text-sm ${
                  actual ? 'text-acento font-bold' : 'text-texto-suave'
                }`}
              >
                <svg aria-hidden="true" viewBox="0 0 20 20" className="size-6">
                  <path fill="currentColor" fillRule="evenodd" d={ICONOS[id]} />
                </svg>
                <span className={actual ? 'underline decoration-2 underline-offset-4' : undefined}>
                  {nombre}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
