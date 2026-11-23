import { Component, type ReactNode } from 'react';

interface Props {
  alternativa: ReactNode;
  children: ReactNode;
}

/** Si una parte falla (por ejemplo, no se pudo descargar el código del mapa), muestra un aviso. */
export class LimiteError extends Component<Props, { fallo: boolean }> {
  override state = { fallo: false };

  static getDerivedStateFromError() {
    return { fallo: true };
  }

  override render() {
    return this.state.fallo ? this.props.alternativa : this.props.children;
  }
}
