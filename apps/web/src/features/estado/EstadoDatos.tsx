import type { Manifiesto } from '@radar/contratos';
import { useEffect, useState } from 'react';
import { describirAntiguedad } from './antiguedad';
import { leerManifiesto } from './manifiesto';

type Estado =
  | { tipo: 'cargando' }
  | { tipo: 'sin-datos' }
  | { tipo: 'error' }
  | { tipo: 'listo'; manifiesto: Manifiesto };

interface Props {
  leer?: () => Promise<Manifiesto | null>;
  ahora?: () => Date;
}

/** Muestra si hay datos publicados y qué tan recientes son. */
export function EstadoDatos({ leer = leerManifiesto, ahora = () => new Date() }: Props) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'cargando' });

  useEffect(() => {
    let vigente = true;
    leer()
      .then((manifiesto) => {
        if (vigente) setEstado(manifiesto ? { tipo: 'listo', manifiesto } : { tipo: 'sin-datos' });
      })
      .catch(() => {
        if (vigente) setEstado({ tipo: 'error' });
      });
    return () => {
      vigente = false;
    };
  }, [leer]);

  return (
    <section aria-live="polite" className="bg-superficie rounded-xl p-4">
      <h2 className="font-semibold">Estado de los datos</h2>
      <p className="text-texto-suave mt-1">{mensaje(estado, ahora())}</p>
    </section>
  );
}

function mensaje(estado: Estado, ahora: Date): string {
  switch (estado.tipo) {
    case 'cargando':
      return 'Consultando…';
    case 'sin-datos':
      return 'Aún no hay datos publicados. Estamos preparando la primera versión.';
    case 'error':
      return 'No pudimos consultar los datos. Revisa tu conexión e inténtalo de nuevo.';
    case 'listo': {
      const { generado_en, productos } = estado.manifiesto;
      const antiguedad = describirAntiguedad(new Date(generado_en), ahora);
      return `Actualizado ${antiguedad} · ${productos.length} producto(s) disponibles.`;
    }
  }
}
