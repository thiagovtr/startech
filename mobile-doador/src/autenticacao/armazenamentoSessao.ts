import * as SecureStore from 'expo-secure-store';

const CHAVE_SESSAO = 'startech.sessao';

export type SessaoAutenticada = {
  accessToken: string;
  expiresIn?: number;
  issuedAt: number;
  refreshToken?: string;
};

export async function obterSessaoArmazenada(): Promise<SessaoAutenticada | null> {
  const sessaoSerializada = await SecureStore.getItemAsync(CHAVE_SESSAO);

  if (!sessaoSerializada) {
    return null;
  }

  try {
    return JSON.parse(sessaoSerializada) as SessaoAutenticada;
  } catch {
    await limparSessaoArmazenada();
    return null;
  }
}

export async function salvarSessaoArmazenada(sessao: SessaoAutenticada): Promise<void> {
  await SecureStore.setItemAsync(CHAVE_SESSAO, JSON.stringify(sessao));
}

export async function limparSessaoArmazenada(): Promise<void> {
  await SecureStore.deleteItemAsync(CHAVE_SESSAO);
}
