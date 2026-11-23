import { EnlaceExterno } from '../../comun/Enlaces';
import { FUENTES, TEXTOS_ACERCA } from './textos';

export function PantallaAcerca() {
  return (
    <div className="pantalla">
      <h1 id="titulo-seccion" tabIndex={-1} className="text-3xl font-bold">
        {TEXTOS_ACERCA.titulo}
      </h1>
      <p>{TEXTOS_ACERCA.presentacion}</p>

      <section aria-labelledby="titulo-fuentes" className="flex flex-col gap-3">
        <h2 id="titulo-fuentes" className="text-xl font-bold">
          {TEXTOS_ACERCA.tituloFuentes}
        </h2>
        <ul className="flex flex-col gap-3">
          {FUENTES.map(({ nombre, aporta, url }) => (
            <li key={nombre}>
              <EnlaceExterno href={url}>{nombre}</EnlaceExterno>
              <span>: {aporta}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
