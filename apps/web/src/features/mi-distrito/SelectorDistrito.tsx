import {
  useDeferredValue,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { ID_TITULO, useEnfocarTituloAlCambiar } from '../../comun/foco';
import { buscar, prepararIndice } from './busqueda';
import type { Catalogo, DistritoLista } from './catalogo';
import { distritoMasCercano } from './geo';
import {
  TEXTOS_SELECTOR,
  textoConfirmarUbicacion,
  textoCuantosResultados,
  textoResultado,
  textoTituloDistritos,
  textoTituloProvincias,
} from './textos';
import type { Geolocalizador } from './ubicacion';

type Paso =
  | { tipo: 'inicio' }
  | { tipo: 'provincias'; departamento: string }
  | { tipo: 'distritos'; departamento: string; provincia: string }
  | { tipo: 'confirmar'; distrito: DistritoLista };

type EstadoUbicacion = 'inactiva' | 'buscando' | 'fuera' | 'fallo';

const clavePaso = (paso: Paso): string => {
  switch (paso.tipo) {
    case 'inicio':
      return 'inicio';
    case 'provincias':
      return `provincias:${paso.departamento}`;
    case 'distritos':
      return `distritos:${paso.departamento}:${paso.provincia}`;
    case 'confirmar':
      return `confirmar:${paso.distrito.ubigeo}`;
  }
};

interface Props {
  catalogo: Catalogo;
  geolocalizador: Geolocalizador;
  onElegir: (distrito: DistritoLista) => void;
  /** Contenido extra al final del primer paso (p. ej. volver al distrito guardado). */
  pie?: ReactNode;
}

const CLASE_OPCION = 'boton boton-secundario w-full justify-start text-left';

/** Elegir distrito: buscador, ubicación del celular y lista en tres pasos. */
export function SelectorDistrito({ catalogo, geolocalizador, onElegir, pie }: Props) {
  const [paso, setPaso] = useState<Paso>({ tipo: 'inicio' });
  const [consulta, setConsulta] = useState('');
  const [ubicacion, setUbicacion] = useState<EstadoUbicacion>('inactiva');
  useEnfocarTituloAlCambiar(clavePaso(paso));

  // Una respuesta de la geolocalización que llega después de desmontar no debe aplicarse.
  const montado = useRef(true);
  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  const usarUbicacion = () => {
    setUbicacion('buscando');
    geolocalizador.obtener().then(
      (punto) => {
        if (!montado.current) return;
        // La posición se usa aquí y se descarta: solo se guarda el ubigeo que se confirme.
        const cercania = distritoMasCercano(catalogo.distritos, punto);
        if (cercania.tipo === 'fuera') {
          setUbicacion('fuera');
        } else {
          setUbicacion('inactiva');
          setPaso({ tipo: 'confirmar', distrito: cercania.distrito });
        }
      },
      () => {
        if (montado.current) setUbicacion('fallo');
      },
    );
  };

  const volverAlInicio = () => setPaso({ tipo: 'inicio' });

  switch (paso.tipo) {
    case 'confirmar':
      return (
        <div className="pantalla">
          <h1 id={ID_TITULO} tabIndex={-1} className="text-3xl font-bold">
            {textoConfirmarUbicacion(paso.distrito)}
          </h1>
          <div className="flex flex-col gap-3">
            <button type="button" className="boton w-full" onClick={() => onElegir(paso.distrito)}>
              {TEXTOS_SELECTOR.confirmarSi}
            </button>
            <button
              type="button"
              className="boton boton-secundario w-full"
              onClick={volverAlInicio}
            >
              {TEXTOS_SELECTOR.confirmarNo}
            </button>
          </div>
        </div>
      );

    case 'provincias':
      return (
        <PasoLista
          titulo={textoTituloProvincias(paso.departamento)}
          alVolver={volverAlInicio}
          opciones={catalogo.provincias(paso.departamento).map((provincia) => ({
            clave: provincia,
            texto: provincia,
            alElegir: () =>
              setPaso({ tipo: 'distritos', departamento: paso.departamento, provincia }),
          }))}
        />
      );

    case 'distritos':
      return (
        <PasoLista
          titulo={textoTituloDistritos(paso.provincia)}
          alVolver={() => setPaso({ tipo: 'provincias', departamento: paso.departamento })}
          opciones={catalogo.distritosDe(paso.departamento, paso.provincia).map((distrito) => ({
            clave: distrito.ubigeo,
            texto: distrito.nombre,
            alElegir: () => onElegir(distrito),
          }))}
        />
      );

    case 'inicio':
      return (
        <div className="pantalla">
          <div className="flex flex-col gap-2">
            <h1 id={ID_TITULO} tabIndex={-1} className="text-3xl font-bold">
              {TEXTOS_SELECTOR.titulo}
            </h1>
            <p>{TEXTOS_SELECTOR.explicacion}</p>
          </div>

          <Buscador
            catalogo={catalogo}
            consulta={consulta}
            setConsulta={setConsulta}
            onElegir={onElegir}
          />

          <div className="flex flex-col gap-2">
            <button
              type="button"
              className="boton w-full"
              // `aria-disabled` y no `disabled`: el botón no pierde el foco mientras se busca.
              aria-disabled={ubicacion === 'buscando'}
              onClick={() => {
                if (ubicacion !== 'buscando') usarUbicacion();
              }}
            >
              {TEXTOS_SELECTOR.usarUbicacion}
            </button>
            <p role="status" className="empty:sr-only">
              {ubicacion === 'buscando' && TEXTOS_SELECTOR.buscandoUbicacion}
            </p>
            {ubicacion === 'fuera' && <p role="alert">{TEXTOS_SELECTOR.fueraDeZona}</p>}
            {ubicacion === 'fallo' && <p role="alert">{TEXTOS_SELECTOR.falloUbicacion}</p>}
          </div>

          <section aria-labelledby="titulo-lista" className="flex flex-col gap-3">
            <h2 id="titulo-lista" className="text-xl font-bold">
              {TEXTOS_SELECTOR.tituloLista}
            </h2>
            <ul className="flex flex-col gap-2">
              {catalogo.departamentos().map((departamento) => (
                <li key={departamento}>
                  <button
                    type="button"
                    className={CLASE_OPCION}
                    onClick={() => setPaso({ tipo: 'provincias', departamento })}
                  >
                    {departamento}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          {pie}
        </div>
      );
  }
}

function Buscador({
  catalogo,
  consulta,
  setConsulta,
  onElegir,
}: {
  catalogo: Catalogo;
  consulta: string;
  setConsulta: (valor: string) => void;
  onElegir: (distrito: DistritoLista) => void;
}) {
  const id = useId();
  // Se normaliza la lista una vez; en cada tecla solo se normaliza lo escrito.
  const indice = useMemo(() => prepararIndice(catalogo.distritos), [catalogo]);
  // Pintar muchos resultados no debe retrasar lo que se escribe.
  const consultaDiferida = useDeferredValue(consulta);
  const resultados = useMemo(() => buscar(indice, consultaDiferida), [indice, consultaDiferida]);
  const hayConsulta = consultaDiferida.trim() !== '';

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={`${id}-campo`} className="font-semibold">
        {TEXTOS_SELECTOR.etiquetaBuscador}
      </label>
      <input
        id={`${id}-campo`}
        type="search"
        value={consulta}
        onChange={(evento) => setConsulta(evento.target.value)}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        enterKeyHint="search"
        aria-controls={`${id}-resultados`}
        className="min-h-11 w-full rounded-lg border-2 border-white bg-white px-3 py-2 text-fondo"
      />
      {/* Siempre presente para que los lectores de pantalla anuncien sus cambios. */}
      <div role="status" className="empty:sr-only">
        {hayConsulta &&
          (resultados.length > 0 ? (
            <span className="sr-only">{textoCuantosResultados(resultados.length)}</span>
          ) : (
            <p>{TEXTOS_SELECTOR.sinResultados}</p>
          ))}
      </div>
      <ul
        id={`${id}-resultados`}
        aria-label={TEXTOS_SELECTOR.resultados}
        className="flex flex-col gap-2 empty:hidden"
      >
        {resultados.map((distrito) => (
          <li key={distrito.ubigeo}>
            <button type="button" className={CLASE_OPCION} onClick={() => onElegir(distrito)}>
              {textoResultado(distrito)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PasoLista({
  titulo,
  alVolver,
  opciones,
}: {
  titulo: string;
  alVolver: () => void;
  opciones: readonly { clave: string; texto: string; alElegir: () => void }[];
}) {
  return (
    <div className="pantalla">
      <div className="flex flex-col items-start gap-3">
        <button type="button" className="boton boton-secundario" onClick={alVolver}>
          {TEXTOS_SELECTOR.volver}
        </button>
        <h1 id={ID_TITULO} tabIndex={-1} className="text-3xl font-bold">
          {titulo}
        </h1>
      </div>
      <ul className="flex flex-col gap-2">
        {opciones.map(({ clave, texto, alElegir }) => (
          <li key={clave}>
            <button type="button" className={CLASE_OPCION} onClick={alElegir}>
              {texto}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
