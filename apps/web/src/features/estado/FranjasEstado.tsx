import { EnlaceExterno } from '../../comun/Enlaces';
import { Icono, type NombreIcono } from '../../comun/Iconos';
import { TEXTOS_COMUNES, URL_AVISOS_SENAMHI } from '../../comun/textos';
import { admiteReintento, type Franja, type Vista } from './estadoProducto';
import { TEXTOS_ESTADO, textoActualizado, textoFranja } from './textos';

const ICONO: Record<Franja['tipo'], NombreIcono | null> = {
  cargando: null,
  lenta: 'reloj',
  'sin-datos': 'info',
  'sin-conexion-con-dato': 'sinConexion',
  'sin-conexion-sin-dato': 'sinConexion',
  error: 'alerta',
  antiguo: 'reloj',
};

interface Props<T> {
  vista: Vista<T>;
  ahora: Date;
  reintentar: () => void;
}

/**
 * Franjas de estado de un producto y la hora del dato, para poner antes de su contenido.
 * Es la pieza común a toda pantalla que muestre un producto del manifiesto.
 */
export function FranjasEstado<T>({ vista, ahora, reintentar }: Props<T>) {
  return (
    <div className="flex flex-col gap-2">
      {vista.franjas.map((franja) => {
        const icono = ICONO[franja.tipo];
        return (
          <div
            key={franja.tipo}
            role="status"
            className={
              franja.tipo === 'cargando'
                ? 'text-texto-suave'
                : `bg-superficie flex flex-col gap-2 rounded-lg border-l-4 border-white p-3 ${
                    // "Sin conexión" queda fija arriba mientras se recorre la pantalla.
                    franja.tipo === 'sin-conexion-con-dato' ? 'sticky top-0 z-10' : ''
                  }`
            }
          >
            <p className="flex items-start gap-2 font-semibold">
              {icono && <Icono nombre={icono} className="mt-0.5 size-5" />}
              <span>{textoFranja(franja, ahora)}</span>
            </p>
            {admiteReintento(franja) && (
              <button type="button" className="boton self-start" onClick={reintentar}>
                {TEXTOS_ESTADO.reintentar}
              </button>
            )}
            {franja.tipo === 'error' && (
              <p>
                <EnlaceExterno href={URL_AVISOS_SENAMHI}>
                  {TEXTOS_COMUNES.verAvisosSenamhi}
                </EnlaceExterno>
              </p>
            )}
          </div>
        );
      })}
      {vista.momento && (
        <p className="text-texto-suave text-sm">{textoActualizado(vista.momento, ahora)}</p>
      )}
    </div>
  );
}
