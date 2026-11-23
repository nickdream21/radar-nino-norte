import type {
  BloqueEnfen,
  BloqueIcen,
  BloqueIndicesSemanales,
  BloqueMarPaita,
  EstadoNino,
} from '@radar/contratos';
import type { ReactNode } from 'react';
import { AvisoNoOficial, EnlaceExterno } from '../../comun/Enlaces';
import { formatearFecha, formatearMes } from '../../comun/hora';
import { Icono } from '../../comun/Iconos';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from '../../comun/textos';
import { FranjasEstado } from '../estado/FranjasEstado';
import type { Resultado } from '../estado/manifiesto';
import { TEXTOS_ESTADO } from '../estado/textos';
import { useProducto, type Dependencias } from '../estado/useProducto';
import { EnlaceSeccion } from '../navegacion/EnlaceSeccion';
import { ID_ESTADO_NINO, comunicadoEsAntiguo, esEstadoNino, leerEstadoNino } from './estadoNino';
import {
  TEXTOS_EL_NINO,
  partesCifraMar,
  textoEstadoOficial,
  textoExplicacionEnfen,
  textoExplicacionMar,
  textoIcen,
  textoNino12,
} from './textos';

interface Props extends Dependencias {
  leer?: () => Promise<Resultado<EstadoNino>>;
}

/** Estado de El Niño costero: lo oficial primero, luego el mar y qué significa. */
export function PantallaElNino({ leer = leerEstadoNino, ...dependencias }: Props) {
  const { vista, ahora, reintentar } = useProducto({
    id: ID_ESTADO_NINO,
    leer,
    validar: esEstadoNino,
    ...dependencias,
  });
  const datos = vista.copia?.datos ?? null;

  return (
    <div className="pantalla">
      <h1 id="titulo-seccion" tabIndex={-1} className="text-3xl font-bold">
        {TEXTOS_EL_NINO.titulo}
      </h1>

      <FranjasEstado vista={vista} ahora={ahora} reintentar={reintentar} />

      {datos && (
        <>
          <EstadoOficial enfen={datos.enfen} ahora={ahora} />
          <MarPaita mar={datos.mar_paita} ahora={ahora} />
        </>
      )}

      <Significado />

      {datos && <Especialistas indices={datos.indices_semanales} icen={datos.icen} ahora={ahora} />}

      <footer className="flex flex-col gap-4">
        <p>{TEXTOS_EL_NINO.cierre}</p>
        <AvisoNoOficial />
        <p>
          <EnlaceSeccion a="acerca">{TEXTOS_COMUNES.acerca}</EnlaceSeccion>
        </p>
      </footer>
    </div>
  );
}

function Tarjeta({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="tarjeta">
      <h2 id={id} className="text-xl font-bold">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

function SinDato() {
  return <p className="font-semibold">{TEXTOS_ESTADO.faltaDato}</p>;
}

function EstadoOficial({ enfen, ahora }: { enfen: BloqueEnfen | null; ahora: Date }) {
  if (!enfen) {
    return (
      <Tarjeta id="titulo-oficial" titulo={TEXTOS_EL_NINO.estadoOficialSinDato}>
        <SinDato />
      </Tarjeta>
    );
  }
  const { comunicado } = enfen;
  const fecha = new Date(comunicado.fecha);
  return (
    <Tarjeta id="titulo-oficial" titulo={textoEstadoOficial(comunicado.estado)}>
      <p>{textoExplicacionEnfen(formatearFecha(fecha, ahora))}</p>
      {comunicadoEsAntiguo(fecha, ahora) && (
        <p className="font-semibold">{TEXTOS_EL_NINO.comunicadoAntiguo}</p>
      )}
      <p>
        <EnlaceExterno href={comunicado.enlace}>{TEXTOS_EL_NINO.leerComunicado}</EnlaceExterno>
      </p>
    </Tarjeta>
  );
}

function MarPaita({ mar, ahora }: { mar: BloqueMarPaita | null; ahora: Date }) {
  return (
    <Tarjeta id="titulo-mar" titulo={TEXTOS_EL_NINO.tituloMar}>
      {mar ? (
        <>
          <CifraMar anomalia={mar.anomalia} />
          <p>{textoExplicacionMar(formatearFecha(new Date(mar.fecha_dato), ahora))}</p>
          <p className="text-texto-suave text-sm">{TEXTOS_EL_NINO.fuenteMar}</p>
        </>
      ) : (
        <SinDato />
      )}
    </Tarjeta>
  );
}

function CifraMar({ anomalia }: { anomalia: number }) {
  const { cifra, comparacion } = partesCifraMar(anomalia);
  return (
    <p>
      <span className="block text-4xl font-bold">{cifra}</span>
      {comparacion && <span className="text-lg font-semibold">{comparacion}</span>}
    </p>
  );
}

function Significado() {
  const { texto, enlace, final, destino } = TEXTOS_EL_NINO.significadoAccion;
  return (
    <Tarjeta id="titulo-significado" titulo={TEXTOS_EL_NINO.tituloSignificado}>
      {TEXTOS_EL_NINO.significado.map((parrafo) => (
        <p key={parrafo}>{parrafo}</p>
      ))}
      <p>
        {texto}
        {destino === 'senamhi' ? (
          <EnlaceExterno href={URL_AVISOS_SENAMHI}>{enlace}</EnlaceExterno>
        ) : (
          <EnlaceSeccion a="mi-distrito">{enlace}</EnlaceSeccion>
        )}
        {final}
      </p>
    </Tarjeta>
  );
}

function Especialistas({
  indices,
  icen,
  ahora,
}: {
  indices: BloqueIndicesSemanales | null;
  icen: BloqueIcen | null;
  ahora: Date;
}) {
  return (
    <details className="tarjeta group">
      <summary className="-m-2 flex min-h-11 cursor-pointer items-center justify-between gap-2 rounded-lg p-2">
        <h2 className="min-w-0 text-xl font-bold">{TEXTOS_EL_NINO.tituloEspecialistas}</h2>
        <Icono nombre="abajo" className="size-6 group-open:rotate-180" />
      </summary>
      <div className="mt-2 flex flex-col gap-4">
        <section className="flex flex-col gap-1">
          <h3 className="text-lg font-bold">{TEXTOS_EL_NINO.tituloNino12}</h3>
          {indices ? (
            <p>
              {textoNino12(
                indices.nino12.ultimo.anomalia,
                indices.nino12.ultimo.temperatura,
                // La fuente da el día central de la semana a las 00:00 UTC: es un día de calendario.
                formatearFecha(new Date(indices.nino12.ultimo.fecha), ahora, 'utc'),
              )}
            </p>
          ) : (
            <SinDato />
          )}
        </section>
        <section className="flex flex-col gap-1">
          <h3 className="text-lg font-bold">{TEXTOS_EL_NINO.tituloIcen}</h3>
          {icen ? (
            <p>{textoIcen(icen.ultimo.valor, formatearMes(icen.ultimo.anio, icen.ultimo.mes))}</p>
          ) : (
            <SinDato />
          )}
        </section>
      </div>
    </details>
  );
}
