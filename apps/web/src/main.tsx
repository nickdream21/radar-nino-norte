import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { prepararHistorial } from './features/navegacion/secciones';
import './index.css';

const raiz = document.getElementById('raiz');
if (!raiz) throw new Error('Falta el elemento #raiz en index.html');

prepararHistorial();

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
