import { CAPAS, type IdCapa } from './capas';
import { esAntigua } from './tiempo';
import { TEXTOS_CAPAS, TEXTOS_MAPA, textoHoraImagen } from './textos';

export type EstadoCapa =
  | { tipo: 'apagada' }
  | { tipo: 'cargando' }
  | { tipo: 'sin-datos' }
  | { tipo: 'error' }
  | { tipo: 'lista'; tiempo: Date; falloImagen: boolean };

interface Props {
  estados: Record<IdCapa, EstadoCapa>;
  ahora: Date;
  alAlternar: (id: IdCapa) => void;
  alReintentar: (id: IdCapa) => void;
}

/** Interruptores de las capas y, para cada capa encendida, de qué hora es su imagen. */
export function ControlCapas({ estados, ahora, alAlternar, alReintentar }: Props) {
  return (
    <section
      aria-labelledby="titulo-capas"
      className="bg-fondo max-h-[45dvh] overflow-y-auto px-4 pt-2 pb-3"
    >
      <h2 id="titulo-capas" className="sr-only">
        {TEXTOS_MAPA.tituloCapas}
      </h2>
      <ul className="flex flex-col gap-1">
        {CAPAS.map(({ id, antiguaTrasMin }) => {
          const estado = estados[id];
          const encendida = estado.tipo !== 'apagada';
          const idEstado = `estado-capa-${id}`;
          return (
            <li key={id}>
              <label className="flex min-h-11 cursor-pointer items-center gap-3 py-1">
                <input
                  type="checkbox"
                  className="accent-acento size-6 shrink-0"
                  checked={encendida}
                  onChange={() => alAlternar(id)}
                  aria-describedby={encendida ? idEstado : undefined}
                />
                <span className="flex-1 font-semibold">{TEXTOS_CAPAS[id].nombre}</span>
                <span className="text-texto-suave text-sm">
                  {encendida ? TEXTOS_MAPA.encendida : TEXTOS_MAPA.apagada}
                </span>
              </label>
              {encendida && (
                <div id={idEstado} aria-live="polite" className="pb-2 pl-9 text-sm">
                  <DetalleCapa
                    estado={estado}
                    ahora={ahora}
                    antiguaTrasMin={antiguaTrasMin}
                    alReintentar={() => alReintentar(id)}
                  />
                  <p className="text-texto-suave mt-0.5">{TEXTOS_CAPAS[id].descripcion}</p>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function DetalleCapa({
  estado,
  ahora,
  antiguaTrasMin,
  alReintentar,
}: {
  estado: EstadoCapa;
  ahora: Date;
  antiguaTrasMin: number;
  alReintentar: () => void;
}) {
  switch (estado.tipo) {
    case 'apagada':
      return null;
    case 'cargando':
      return <p>{TEXTOS_MAPA.consultandoHora}</p>;
    case 'sin-datos':
      return <Aviso>{TEXTOS_MAPA.sinDatos}</Aviso>;
    case 'error':
      return (
        <div className="flex flex-wrap items-center gap-x-3">
          <Aviso>{TEXTOS_MAPA.errorHora}</Aviso>
          <button
            type="button"
            onClick={alReintentar}
            className="text-acento min-h-11 font-semibold underline underline-offset-4"
          >
            {TEXTOS_MAPA.reintentar}
          </button>
        </div>
      );
    case 'lista':
      return (
        <>
          <p>{textoHoraImagen(estado.tiempo, ahora)}</p>
          {esAntigua(estado.tiempo, ahora, antiguaTrasMin) && <Aviso>{TEXTOS_MAPA.antigua}</Aviso>}
          {estado.falloImagen && <Aviso>{TEXTOS_MAPA.errorImagen}</Aviso>}
        </>
      );
  }
}

/** Aviso con icono y texto: el color nunca es la única señal. */
function Aviso({ children }: { children: string }) {
  return (
    <p className="text-acento flex items-start gap-1.5 font-semibold">
      <svg aria-hidden="true" viewBox="0 0 20 20" className="mt-0.5 size-4 shrink-0">
        <path
          fill="currentColor"
          d="M10 1.5 19 18H1L10 1.5Zm-1 6v5h2v-5H9Zm0 6.5v2h2v-2H9Z"
          fillRule="evenodd"
        />
      </svg>
      {children}
    </p>
  );
}
