import { describe, expect, it, vi } from 'vitest';
import { CAPAS, type IdCapa } from './capas';
import { crearLectorHora } from './horaCapas';
import infrarrojo from './respuestas/gibs-dominios-infrarrojo-2026-11-23.xml?raw';
import nowcoast from './respuestas/nowcoast-capacidades-2026-11-23.xml?raw';

const ahora = () => new Date('2026-11-23T14:39:00Z');
const capa = (id: IdCapa) => {
  const encontrada = CAPAS.find((candidata) => candidata.id === id);
  if (!encontrada) throw new Error(id);
  return encontrada;
};
const responder =
  (cuerpo: string, status = 200) =>
  () =>
    Promise.resolve(new Response(cuerpo, { status }));

describe('crearLectorHora', () => {
  it('consulta DescribeDomains de GIBS y devuelve la última hora', async () => {
    const pedir = vi.fn(responder(infrarrojo));
    const leer = crearLectorHora(pedir, ahora);

    await expect(leer(capa('satelite'))).resolves.toEqual(new Date('2026-11-23T13:50:00Z'));
    expect(pedir).toHaveBeenCalledWith(
      expect.stringContaining(
        '/GOES-East_ABI_Band13_Clean_Infrared/default/GoogleMapsCompatible_Level6/all/',
      ),
    );
  });

  it('consulta el GetCapabilities de nowCOAST para los rayos', async () => {
    const pedir = vi.fn(responder(nowcoast));
    const leer = crearLectorHora(pedir, ahora);

    await expect(leer(capa('rayos'))).resolves.toEqual(new Date('2026-11-23T14:15:00Z'));
    expect(pedir).toHaveBeenCalledWith(expect.stringContaining('request=GetCapabilities'));
  });

  it('falla si el servicio responde con error', async () => {
    const leer = crearLectorHora(responder('caído', 503), ahora);
    await expect(leer(capa('lluvia'))).rejects.toThrow('503');
  });
});
