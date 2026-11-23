import { useState } from 'react';
import { ID_TITULO, useEnfocarTituloAlCambiar } from '../../comun/foco';
import { Icono } from '../../comun/Iconos';
import { TEXTOS_COMUNES } from '../../comun/textos';
import { EnlaceSeccion } from '../navegacion/EnlaceSeccion';
import { SECCIONES } from '../navegacion/secciones';
import { CATALOGO, type Catalogo, type DistritoLista } from './catalogo';
import { preferenciaNavegador, type PreferenciaDistrito } from './preferencia';
import { PronosticoDistrito } from './PronosticoDistrito';
import { SelectorDistrito } from './SelectorDistrito';
import { TEXTOS_MI_DISTRITO, textoUbicacionDistrito } from './textos';
import { geolocalizadorNavegador, type Geolocalizador } from './ubicacion';

interface Props {
  catalogo?: Catalogo;
  preferencia?: PreferenciaDistrito;
  geolocalizador?: Geolocalizador;
}

/**
 * Mi distrito: la primera vez pide elegir el distrito; después muestra el distrito guardado.
 * Un ubigeo guardado que ya no está en la lista se trata como si no hubiera ninguno.
 */
export function PantallaMiDistrito({
  catalogo = CATALOGO,
  preferencia = preferenciaNavegador,
  geolocalizador = geolocalizadorNavegador,
}: Props) {
  const [distrito, setDistrito] = useState<DistritoLista | null>(() => {
    const ubigeo = preferencia.leer();
    return (ubigeo && catalogo.porUbigeo(ubigeo)) || null;
  });
  const [cambiando, setCambiando] = useState(false);
  useEnfocarTituloAlCambiar(distrito && !cambiando ? `distrito:${distrito.ubigeo}` : 'selector');

  const elegir = (elegido: DistritoLista) => {
    preferencia.guardar(elegido.ubigeo);
    setDistrito(elegido);
    setCambiando(false);
  };

  if (!distrito || cambiando) {
    return (
      <SelectorDistrito
        catalogo={catalogo}
        geolocalizador={geolocalizador}
        onElegir={elegir}
        pie={
          <footer className="mt-auto flex flex-col items-start gap-4">
            {distrito && (
              <button
                type="button"
                className="boton boton-secundario"
                onClick={() => setCambiando(false)}
              >
                {TEXTOS_MI_DISTRITO.cancelarCambio}
              </button>
            )}
            <EnlaceSeccion a="acerca">{TEXTOS_COMUNES.acerca}</EnlaceSeccion>
          </footer>
        }
      />
    );
  }

  return (
    <div className="pantalla">
      <div className="flex flex-col items-start gap-3">
        <div className="flex flex-col gap-1">
          <h1 id={ID_TITULO} tabIndex={-1} className="text-3xl font-bold">
            {distrito.nombre}
          </h1>
          <p className="text-texto-suave text-lg">{textoUbicacionDistrito(distrito)}</p>
        </div>
        <button type="button" className="boton boton-secundario" onClick={() => setCambiando(true)}>
          {TEXTOS_MI_DISTRITO.cambiarDistrito}
        </button>
      </div>

      <PronosticoDistrito distrito={distrito} />

      <ul className="flex flex-col gap-3">
        <li>
          <EnlaceSeccion a="el-nino" className="boton w-full justify-start">
            <Icono nombre="ola" className="size-6" />
            {SECCIONES['el-nino'].nombre}
          </EnlaceSeccion>
        </li>
        <li>
          <EnlaceSeccion a="mapa" className="boton w-full justify-start">
            <Icono nombre="mapa" className="size-6" />
            {SECCIONES.mapa.nombre}
          </EnlaceSeccion>
        </li>
      </ul>

      <footer className="mt-auto">
        <EnlaceSeccion a="acerca">{TEXTOS_COMUNES.acerca}</EnlaceSeccion>
      </footer>
    </div>
  );
}
