import { Suspense, lazy, useEffect, useRef } from 'react';
import { LimiteError } from './comun/LimiteError';
import { PantallaInicio } from './features/inicio/PantallaInicio';
import { BarraNavegacion } from './features/navegacion/BarraNavegacion';
import { useSeccion } from './features/navegacion/secciones';

// El mapa y MapLibre se descargan solo al abrir la sección Mapa.
const SeccionMapa = lazy(() => import('./features/mapa/SeccionMapa'));

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
      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {seccion === 'mapa' ? (
          <LimiteError
            alternativa={
              <p role="alert" className="m-auto p-6 font-semibold">
                No pudimos abrir el mapa. Revisa tu conexión e inténtalo de nuevo.
              </p>
            }
          >
            <Suspense fallback={<p className="text-texto-suave m-auto p-6">Cargando el mapa…</p>}>
              <SeccionMapa />
            </Suspense>
          </LimiteError>
        ) : (
          <PantallaInicio />
        )}
      </main>
      <BarraNavegacion activa={seccion} />
    </div>
  );
}
