import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { defineConfig } from 'vitest/config';

// En GitHub Pages la app vive en /<repositorio>/; el despliegue define RADAR_BASE.
const base = process.env.RADAR_BASE ?? '/';

export default defineConfig({
  base,
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Radar Niño Norte',
        short_name: 'Radar Niño',
        description: 'El Niño costero, lluvias, rayos y ríos en el norte del Perú',
        lang: 'es-PE',
        theme_color: '#0b2545',
        background_color: '#0b2545',
        display: 'standalone',
        icons: [
          { src: 'iconos/icono-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'iconos/icono-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'iconos/icono-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Los datos cambian cada pocos minutos: red primero, y el último dato
        // válido guardado cuando no hay conexión.
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.includes('/datos/'),
            handler: 'NetworkFirst',
            options: { cacheName: 'datos', networkTimeoutSeconds: 5 },
          },
        ],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/pruebas/configuracion.ts'],
  },
});
