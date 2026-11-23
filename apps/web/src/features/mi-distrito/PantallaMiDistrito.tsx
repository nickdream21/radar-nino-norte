import { EnlaceExterno } from '../../comun/Enlaces';
import { Icono } from '../../comun/Iconos';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from '../../comun/textos';
import { EnlaceSeccion } from '../navegacion/EnlaceSeccion';
import { SECCIONES } from '../navegacion/secciones';
import { TEXTOS_MI_DISTRITO } from './textos';

/**
 * Mi distrito, mientras no exista el pronóstico por distrito: lo dice con honestidad y lleva
 * a lo que sí hay.
 */
export function PantallaMiDistrito() {
  return (
    <div className="pantalla">
      <h1 id="titulo-seccion" tabIndex={-1} className="text-3xl font-bold">
        {TEXTOS_MI_DISTRITO.titulo}
      </h1>

      <p>
        {TEXTOS_MI_DISTRITO.preparando}{' '}
        <EnlaceExterno href={URL_AVISOS_SENAMHI}>{TEXTOS_COMUNES.verAvisosSenamhi}</EnlaceExterno>
      </p>

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
