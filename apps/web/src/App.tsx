import { Suspense, lazy, useEffect, useRef } from 'react';
import { LimiteError } from './comun/LimiteError';
import { PantallaAcerca } from './features/acerca/PantallaAcerca';
import { PantallaElNino } from './features/el-nino/PantallaElNino';
import { TEXTOS_MAPA } from './features/mapa/textos';
import { PantallaMiDistrito } from './features/mi-distrito/PantallaMiDistrito';
import { BarraNavegacion } from './features/navegacion/BarraNavegacion';
import { BarraSuperior } from './features/navegacion/BarraSuperior';
import { useSeccion, type IdSeccion } from './features/navegacion/secciones';

// El mapa y MapLibre se descargan solo al abrir la sección Mapa.
const SeccionMapa = lazy(() => import('./features/mapa/SeccionMapa'));

function Seccion({ id }: { id: IdSeccion }) {
  switch (id) {
    case 'mi-distrito':
      return <PantallaMiDistrito />;
    case 'el-nino':
      return <PantallaElNino />;
    case 'acerca':
      return <PantallaAcerca />;
    case 'mapa':
      return (
        <>
          {/* El título vive fuera del código diferido para poder recibir el foco al instante. */}
          <h1 id="titulo-seccion" tabIndex={-1} className="sr-only">
            {TEXTOS_MAPA.titulo}
          </h1>
          <LimiteError
            alternativa={
              <p role="alert" className="m-auto p-6 font-semibold">
                {TEXTOS_MAPA.errorCodigoMapa}
              </p>
            }
          >
            <Suspense
              fallback={<p className="text-texto-suave m-auto p-6">{TEXTOS_MAPA.cargandoMapa}</p>}
            >
              <SeccionMapa />
            </Suspense>
          </LimiteError>
        </>
      );
  }
}

export function App() {
  const seccion = useSeccion();
  const anterior = useRef(seccion);

  // Al cambiar de sección, el foco pasa a su título para que los lectores de pantalla la anuncien.
  useEffect(() => {
    if (anterior.current === seccion) return;
    anterior.current = seccion;
    document.getElementById('titulo-seccion')?.focus();
  }, [seccion]);

  return (
    <div className="flex h-dvh flex-col">
      <BarraSuperior />
      {/* `relative`: los textos solo para lectores de pantalla (posición absoluta) quedan
          dentro del área que se desplaza y no alargan la página. */}
      <main className="relative flex min-h-0 flex-1 flex-col overflow-y-auto">
        <Seccion key={seccion} id={seccion} />
      </main>
      <BarraNavegacion activa={seccion} />
    </div>
  );
}
