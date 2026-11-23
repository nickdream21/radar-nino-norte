import { Icono, type NombreIcono } from '../../comun/Iconos';
import { EnlaceSeccion } from './EnlaceSeccion';
import { SECCIONES, SECCIONES_BARRA, type IdSeccion } from './secciones';

const ICONOS: Partial<Record<IdSeccion, NombreIcono>> = {
  'mi-distrito': 'casa',
  mapa: 'mapa',
  'el-nino': 'ola',
};

/**
 * Barra inferior, al alcance del pulgar con el celular en una mano. La sección activa se
 * marca con relleno y negrita, no solo con color.
 */
export function BarraNavegacion({ activa }: { activa: IdSeccion }) {
  return (
    <nav
      aria-label="Secciones"
      className="bg-superficie border-t border-white/20 pb-[env(safe-area-inset-bottom)]"
    >
      <ul className="mx-auto flex max-w-xl gap-1 px-1 py-1">
        {SECCIONES_BARRA.map((id) => {
          const actual = id === activa;
          const icono = ICONOS[id];
          return (
            <li key={id} className="flex flex-1">
              <EnlaceSeccion
                a={id}
                aria-current={actual ? 'page' : undefined}
                className={`flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1 text-center text-sm leading-tight ${
                  actual ? 'bg-white font-bold text-fondo' : 'text-white'
                }`}
              >
                {icono && <Icono nombre={icono} className="size-6" />}
                <span>{SECCIONES[id].nombre}</span>
              </EnlaceSeccion>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
