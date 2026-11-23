import { EstadoDatos } from '../estado/EstadoDatos';

const AVISOS_SENAMHI = 'https://www.senamhi.gob.pe/?p=aviso-meteorologico';

export function PantallaInicio() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 id="titulo-seccion" tabIndex={-1} className="text-3xl font-bold">
          Radar Niño Norte
        </h1>
        <p className="text-texto-suave mt-1">
          El Niño costero, lluvias, rayos y ríos en Tumbes, Piura, Lambayeque, La Libertad y
          Cajamarca.
        </p>
      </header>

      <EstadoDatos />

      <footer className="text-texto-suave mt-auto text-sm">
        Esta app no es una fuente oficial de alertas. Consulta siempre los{' '}
        <a className="text-acento underline" href={AVISOS_SENAMHI} rel="noreferrer" target="_blank">
          avisos de SENAMHI
        </a>
        .
      </footer>
    </div>
  );
}
