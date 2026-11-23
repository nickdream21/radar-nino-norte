import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
} from 'react';
import { CAPAS, urlTeselas, type IdCapa } from './capas';
import { ControlCapas, type EstadoCapa } from './ControlCapas';
import { crearLectorHora, type LectorHora } from './horaCapas';
import { LimiteError } from '../../comun/LimiteError';
import { TEXTOS_MAPA } from './textos';
import type { CapaEnMapa, MotivoFalloMapa, PropsMapa } from './tipos';

const MapaDiferido = lazy(() => import('./MapaVista'));
const lectorReal = crearLectorHora();
const relojReal = () => new Date();

const MINUTO_MS = 60_000;

interface Props {
  leerHora?: LectorHora;
  ahora?: () => Date;
  Mapa?: ComponentType<PropsMapa>;
  /** Capas encendidas al abrir la sección. */
  encendidasAlInicio?: readonly IdCapa[];
  /** Cada cuánto se vuelve a preguntar la hora de las capas encendidas. */
  refrescoMs?: number;
}

type Estados = Record<IdCapa, EstadoCapa>;

function estadosIniciales(encendidas: readonly IdCapa[]): Estados {
  const estados = {} as Estados;
  for (const { id } of CAPAS) {
    estados[id] = encendidas.includes(id) ? { tipo: 'cargando' } : { tipo: 'apagada' };
  }
  return estados;
}

function definicion(id: IdCapa) {
  const capa = CAPAS.find((candidata) => candidata.id === id);
  if (!capa) throw new Error(`Capa desconocida: ${id}`);
  return capa;
}

export function SeccionMapa({
  leerHora = lectorReal,
  ahora = relojReal,
  Mapa = MapaDiferido,
  encendidasAlInicio = ['satelite'],
  refrescoMs = 10 * MINUTO_MS,
}: Props) {
  const [estados, setEstados] = useState(() => estadosIniciales(encendidasAlInicio));
  const [ahoraActual, setAhoraActual] = useState(ahora);
  const [falloMapa, setFalloMapa] = useState<MotivoFalloMapa | null>(null);
  // Número de la última consulta por capa: descarta respuestas que llegan tarde.
  const consultas = useRef<Record<IdCapa, number>>({ satelite: 0, lluvia: 0, rayos: 0 });
  const estadosVigentes = useRef(estados);

  useEffect(() => {
    estadosVigentes.current = estados;
  }, [estados]);

  const consultar = useCallback(
    (id: IdCapa, esRefresco: boolean) => {
      const numero = ++consultas.current[id];
      const vigente = () => consultas.current[id] === numero;
      const actualizar = (cambio: (actual: EstadoCapa) => EstadoCapa) =>
        setEstados((previos) => {
          const actual = previos[id];
          if (actual.tipo === 'apagada') return previos;
          const nuevo = cambio(actual);
          return nuevo === actual ? previos : { ...previos, [id]: nuevo };
        });

      leerHora(definicion(id)).then(
        (tiempo) => {
          if (!vigente()) return;
          setAhoraActual(ahora());
          actualizar((actual) => {
            // Si un refresco no trae nada, la imagen que ya se ve sigue siendo válida.
            if (!tiempo)
              return esRefresco && actual.tipo === 'lista' ? actual : { tipo: 'sin-datos' };
            if (actual.tipo === 'lista' && actual.tiempo.getTime() === tiempo.getTime())
              return actual;
            return { tipo: 'lista', tiempo, falloImagen: false };
          });
        },
        () => {
          if (!vigente()) return;
          // Un refresco fallido no borra la imagen: su antigüedad seguirá a la vista.
          actualizar((actual) =>
            esRefresco && actual.tipo === 'lista' ? actual : { tipo: 'error' },
          );
        },
      );
    },
    [leerHora, ahora],
  );

  // Primera consulta de las capas encendidas al abrir la sección.
  useEffect(() => {
    for (const { id } of CAPAS) {
      if (estadosVigentes.current[id].tipo === 'cargando') consultar(id, false);
    }
  }, [consultar]);

  // El reloj avanza para que la antigüedad mostrada no se quede congelada.
  useEffect(() => {
    const intervalo = setInterval(() => setAhoraActual(ahora()), MINUTO_MS / 2);
    return () => clearInterval(intervalo);
  }, [ahora]);

  useEffect(() => {
    const intervalo = setInterval(() => {
      for (const { id } of CAPAS) {
        if (estadosVigentes.current[id].tipo !== 'apagada') consultar(id, true);
      }
    }, refrescoMs);
    return () => clearInterval(intervalo);
  }, [consultar, refrescoMs]);

  const encender = useCallback(
    (id: IdCapa) => {
      setEstados((previos) => ({ ...previos, [id]: { tipo: 'cargando' } }));
      consultar(id, false);
    },
    [consultar],
  );

  const alAlternar = useCallback(
    (id: IdCapa) => {
      if (estadosVigentes.current[id].tipo === 'apagada') {
        encender(id);
      } else {
        consultas.current[id]++;
        setEstados((previos) => ({ ...previos, [id]: { tipo: 'apagada' } }));
      }
    },
    [encender],
  );

  const alFallarCapa = useCallback((id: IdCapa) => {
    setEstados((previos) => {
      const actual = previos[id];
      if (actual.tipo !== 'lista' || actual.falloImagen) return previos;
      return { ...previos, [id]: { ...actual, falloImagen: true } };
    });
  }, []);

  const capasEnMapa = useMemo<CapaEnMapa[]>(
    () =>
      CAPAS.flatMap((capa) => {
        const estado = estados[capa.id];
        if (estado.tipo !== 'lista') return [];
        return [
          {
            id: capa.id,
            url: urlTeselas(capa, estado.tiempo),
            atribucion: capa.atribucion,
            zoomMaximo: capa.zoomMaximo,
            opacidad: capa.opacidad,
          },
        ];
      }),
    [estados],
  );

  const avisoMapa = (texto: string) => (
    <p
      role="alert"
      className="bg-fondo/90 absolute inset-x-2 top-2 rounded-lg p-3 text-sm font-semibold"
    >
      {texto}
    </p>
  );

  return (
    <section aria-labelledby="titulo-seccion" className="flex min-h-0 flex-1 flex-col">
      <h1 id="titulo-seccion" tabIndex={-1} className="sr-only">
        {TEXTOS_MAPA.titulo}
      </h1>
      <div className="bg-superficie relative min-h-0 flex-1">
        <LimiteError alternativa={avisoMapa(TEXTOS_MAPA.errorMapa)}>
          <Suspense
            fallback={
              <p className="text-texto-suave absolute inset-0 grid place-items-center">
                {TEXTOS_MAPA.cargandoMapa}
              </p>
            }
          >
            <Mapa capas={capasEnMapa} alFallarCapa={alFallarCapa} alFallarMapa={setFalloMapa} />
          </Suspense>
        </LimiteError>
        {falloMapa &&
          avisoMapa(
            falloMapa === 'no-soportado' ? TEXTOS_MAPA.errorMapaNoSoportado : TEXTOS_MAPA.errorMapa,
          )}
      </div>
      <ControlCapas
        estados={estados}
        ahora={ahoraActual}
        alAlternar={alAlternar}
        alReintentar={encender}
      />
    </section>
  );
}

export default SeccionMapa;
