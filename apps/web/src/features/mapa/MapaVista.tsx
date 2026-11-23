/**
 * Mapa con MapLibre. Este módulo se importa de forma diferida: es el único que arrastra
 * MapLibre (unos cientos de kB) y no debe entrar en el paquete de la pantalla de inicio.
 */
import {
  AttributionControl,
  Map as MapaLibre,
  NavigationControl,
  setWorkerUrl,
  type RasterTileSource,
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import urlTrabajador from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { useEffect, useRef } from 'react';
import { CAPAS, LIMITES_MAPA, ZONA_TRABAJO, type IdCapa } from './capas';
import { TEXTOS_MAPA } from './textos';
import type { CapaEnMapa, PropsMapa } from './tipos';

// Tras empaquetar, MapLibre no encuentra su trabajador junto a sí mismo: se lo indicamos.
setWorkerUrl(urlTrabajador);

const ESTILO_BASE = 'https://tiles.openfreemap.org/styles/positron';
const PREFIJO = 'radar-';

const idFuente = (id: IdCapa) => `${PREFIJO}${id}`;

function idCapaDeFuente(fuente: unknown): IdCapa | null {
  if (typeof fuente !== 'string' || !fuente.startsWith(PREFIJO)) return null;
  const id = fuente.slice(PREFIJO.length);
  return CAPAS.some((capa) => capa.id === id) ? (id as IdCapa) : null;
}

/**
 * Pone en el mapa exactamente las capas pedidas, sin recargar el mapa base.
 * `urls` recuerda la URL con la que se creó cada fuente (MapLibre no la expone).
 */
function sincronizar(mapa: MapaLibre, capas: readonly CapaEnMapa[], urls: Map<IdCapa, string>) {
  const pedidas = new Map(capas.map((capa) => [capa.id, capa]));

  for (const { id } of CAPAS) {
    if (pedidas.has(id) || !mapa.getSource(idFuente(id))) continue;
    if (mapa.getLayer(idFuente(id))) mapa.removeLayer(idFuente(id));
    mapa.removeSource(idFuente(id));
    urls.delete(id);
  }

  // De arriba hacia abajo, para saber siempre qué capa nuestra queda encima.
  const primeraEtiqueta = mapa.getStyle().layers.find((capa) => capa.type === 'symbol')?.id;
  let encima: string | undefined = primeraEtiqueta;
  for (const { id } of [...CAPAS].reverse()) {
    const capa = pedidas.get(id);
    if (!capa) continue;
    const fuente = mapa.getSource<RasterTileSource>(idFuente(id));
    if (fuente) {
      if (urls.get(id) !== capa.url) fuente.setTiles([capa.url]);
    } else {
      mapa.addSource(idFuente(id), {
        type: 'raster',
        tiles: [capa.url],
        tileSize: 256,
        maxzoom: capa.zoomMaximo,
        bounds: [...LIMITES_MAPA],
        attribution: capa.atribucion,
      });
      mapa.addLayer(
        {
          id: idFuente(id),
          type: 'raster',
          source: idFuente(id),
          paint: { 'raster-opacity': capa.opacidad },
        },
        encima,
      );
    }
    urls.set(id, capa.url);
    encima = idFuente(id);
  }
}

export default function MapaVista({ capas, alFallarCapa, alFallarMapa }: PropsMapa) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaLibre | null>(null);
  const estiloListo = useRef(false);
  const ultimasCapas = useRef(capas);
  const urls = useRef(new Map<IdCapa, string>());
  const avisos = useRef({ alFallarCapa, alFallarMapa });

  useEffect(() => {
    avisos.current = { alFallarCapa, alFallarMapa };
  });

  /** Aplica las capas; si MapLibre rechaza el cambio, lo avisa sin tumbar el mapa base. */
  const aplicar = useRef((instancia: MapaLibre, pedidas: readonly CapaEnMapa[]) => {
    try {
      sincronizar(instancia, pedidas, urls.current);
    } catch (error) {
      console.error(error);
      for (const capa of pedidas) avisos.current.alFallarCapa(capa.id);
    }
  });

  useEffect(() => {
    if (!contenedor.current) return;
    const urlsCreadas = urls.current;
    let instancia: MapaLibre;
    try {
      instancia = new MapaLibre({
        container: contenedor.current,
        style: ESTILO_BASE,
        bounds: [...ZONA_TRABAJO],
        fitBoundsOptions: { padding: 8 },
        maxBounds: [...LIMITES_MAPA],
        maxZoom: 10,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
      });
    } catch {
      // Sin WebGL MapLibre no puede crear el mapa.
      avisos.current.alFallarMapa('no-soportado');
      return;
    }
    instancia.touchZoomRotate.disableRotation();
    instancia.keyboard.disableRotation();
    instancia.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    // Sin compactar: en un celular el modo compacto esconde la atribución tras un botón.
    instancia.addControl(new AttributionControl({ compact: false }), 'bottom-right');
    instancia.getCanvas().setAttribute('aria-label', TEXTOS_MAPA.etiquetaMapa);

    instancia.on('load', () => {
      estiloListo.current = true;
      aplicar.current(instancia, ultimasCapas.current);
    });
    instancia.on('error', (evento) => {
      const id = idCapaDeFuente((evento as { sourceId?: unknown }).sourceId);
      if (id) avisos.current.alFallarCapa(id);
      else avisos.current.alFallarMapa('red');
    });

    mapa.current = instancia;
    return () => {
      estiloListo.current = false;
      mapa.current = null;
      urlsCreadas.clear();
      instancia.remove();
    };
  }, []);

  useEffect(() => {
    ultimasCapas.current = capas;
    if (mapa.current && estiloListo.current) aplicar.current(mapa.current, capas);
  }, [capas]);

  // MapLibre impone `position: relative` a su contenedor: el posicionamiento va por fuera.
  return (
    <div className="absolute inset-0">
      <div ref={contenedor} className="h-full w-full" />
    </div>
  );
}
