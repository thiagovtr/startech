import type { criarClienteHttp } from './clienteHttp';

type ClienteHttp = ReturnType<typeof criarClienteHttp>;

export type TipoSanguineo = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-';

export type SexoDoador = 'M' | 'F';

export type FormularioPerfil = {
  nome: string;
  tipoSanguineo: TipoSanguineo;
  sexo: SexoDoador;
  dataUltimaDoacao?: string;
};

export type RespostaPerfil = {
  id: string;
  nome: string;
  tipoSanguineo: TipoSanguineo;
  sexo: SexoDoador;
  dataUltimaDoacao: string | null;
};

export async function salvarPerfil(
  clienteHttp: ClienteHttp,
  dados: FormularioPerfil,
): Promise<RespostaPerfil> {
  const resposta = await clienteHttp.requisitar<RespostaPerfil>('/api/mobile/perfil', {
    metodo: 'PUT',
    corpo: dados,
  });

  if (resposta.status !== 200 || !resposta.corpo) {
    throw new Error('A resposta não contém o perfil salvo.');
  }

  return resposta.corpo;
}
