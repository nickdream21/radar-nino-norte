import { describe, expect, it } from 'vitest';
import { crearAlmacenFalso } from '../../pruebas/dobles';
import { CLAVE_DISTRITO, crearPreferenciaDistrito } from './preferencia';

describe('crearPreferenciaDistrito', () => {
  it('guarda solo el ubigeo en el almacenamiento local', () => {
    const almacen = crearAlmacenFalso();
    const preferencia = crearPreferenciaDistrito(almacen);
    expect(preferencia.leer()).toBeNull();

    preferencia.guardar('140306');
    expect(Object.fromEntries(almacen.contenido)).toEqual({ [CLAVE_DISTRITO]: '140306' });
    expect(crearPreferenciaDistrito(almacen).leer()).toBe('140306');
  });

  it('si el almacenamiento no guarda nada (modo privado), recuerda la elección en la sesión', () => {
    const preferencia = crearPreferenciaDistrito({ leer: () => null, guardar: () => {} });
    preferencia.guardar('200101');
    expect(preferencia.leer()).toBe('200101');
  });
});
