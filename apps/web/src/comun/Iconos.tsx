/**
 * Iconos propios en SVG (viewBox 20×20): son pocos y no justifican una librería.
 * Siempre decorativos: el texto de al lado dice lo mismo.
 */
const TRAZOS = {
  casa: 'M10 2 1 9.5V18h6v-5h6v5h6V9.5L10 2Z',
  mapa: 'M1 4.5 7 2l6 2.5L19 2v13.5L13 18l-6-2.5L1 18V4.5Zm6 0v9.4l6 2.5V7L7 4.5Z',
  // Ola
  ola: 'M1 8c2-2 4-2 6 0s4 2 6 0 4-2 6 0v3c-2-2-4-2-6 0s-4 2-6 0-4-2-6 0V8Zm0 6c2-2 4-2 6 0s4 2 6 0 4-2 6 0v3c-2-2-4-2-6 0s-4 2-6 0-4-2-6 0v-3Z',
  externo: 'M11 2h7v7h-2V5.4l-7.3 7.3-1.4-1.4L14.6 4H11V2ZM3 5h6v2H5v8h8v-4h2v6H3V5Z',
  reloj:
    'M10 1a9 9 0 1 1 0 18 9 9 0 0 1 0-18Zm0 2a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm-1 2h2v4.6l3 1.8-1 1.7-4-2.4V5Z',
  sinConexion:
    'M2.3 1 19 17.7 17.7 19l-4.4-4.4a3.9 3.9 0 0 0-6.4.9L5 14a6.3 6.3 0 0 1 4.3-2.9L7.1 8.9A9.3 9.3 0 0 0 2.6 11.5L1 10a11.7 11.7 0 0 1 4.3-2.9L1 2.3 2.3 1ZM10 3c3.6 0 6.8 1.4 9 3.6l-1.6 1.6A10.4 10.4 0 0 0 9.4 5.3L7.3 3.2C8.2 3 9.1 3 10 3Zm0 12.5a1.8 1.8 0 1 1 0 3.5 1.8 1.8 0 0 1 0-3.5Z',
  alerta: 'M10 1.5 19 18H1L10 1.5Zm-1 6v5h2v-5H9Zm0 6.5v2h2v-2H9Z',
  abajo: 'M3.6 6.6 5 5.2l5 5 5-5 1.4 1.4L10 13 3.6 6.6Z',
  info: 'M10 1a9 9 0 1 1 0 18 9 9 0 0 1 0-18Zm-1 8v6h2V9H9Zm0-4v2h2V5H9Z',
} as const;

export type NombreIcono = keyof typeof TRAZOS;

export function Icono({
  nombre,
  className = 'size-5',
}: {
  nombre: NombreIcono;
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 20 20"
      className={`shrink-0 ${className}`}
    >
      <path fill="currentColor" fillRule="evenodd" d={TRAZOS[nombre]} />
    </svg>
  );
}
