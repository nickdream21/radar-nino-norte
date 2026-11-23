import type { Coordenadas } from './geo';

/**
 * Acceso a la ubicación del celular. Inyectable para probar sin la geolocalización real.
 * La posición se usa solo para proponer un distrito: no se guarda ni sale del celular.
 */
export interface Geolocalizador {
  /** Pide la posición (y el permiso, si hace falta). Rechaza si se niega o falla. */
  obtener(): Promise<Coordenadas>;
}

export const geolocalizadorNavegador: Geolocalizador = {
  obtener: () =>
    new Promise((resolver, rechazar) => {
      if (!('geolocation' in navigator)) {
        rechazar(new Error('El navegador no ofrece geolocalización'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => resolver({ latitud: coords.latitude, longitud: coords.longitude }),
        (error) => rechazar(new Error(error.message || `Geolocalización: código ${error.code}`)),
        // Basta con la precisión de la red: se busca la capital más cercana, no una calle.
        { enableHighAccuracy: false, timeout: 20_000, maximumAge: 10 * 60_000 },
      );
    }),
};
