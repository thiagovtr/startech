import { ErroConfiguracaoApi } from './api';

const REALM_KEYCLOAK = 'startech';

export type ConfiguracaoOidc = {
  clientId: string;
  emissor: string;
};

export function obterConfiguracaoOidc(): ConfiguracaoOidc {
  const urlConfigurada = process.env.EXPO_PUBLIC_KEYCLOAK_URL?.trim();
  const clientId = process.env.EXPO_PUBLIC_KEYCLOAK_CLIENT_ID?.trim();

  if (!urlConfigurada) {
    throw new ErroConfiguracaoApi(
      'A variável EXPO_PUBLIC_KEYCLOAK_URL não foi configurada. Defina a URL pública do Keycloak.',
    );
  }

  if (!clientId) {
    throw new ErroConfiguracaoApi('A variável EXPO_PUBLIC_KEYCLOAK_CLIENT_ID não foi configurada.');
  }

  let urlKeycloak: URL;

  try {
    urlKeycloak = new URL(urlConfigurada);
  } catch {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_KEYCLOAK_URL deve conter uma URL válida do Keycloak.');
  }

  if (!['http:', 'https:'].includes(urlKeycloak.protocol) || urlKeycloak.username || urlKeycloak.password) {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_KEYCLOAK_URL deve usar http ou https, sem credenciais na URL.');
  }

  if (urlKeycloak.pathname !== '/' || urlKeycloak.search || urlKeycloak.hash) {
    throw new ErroConfiguracaoApi('EXPO_PUBLIC_KEYCLOAK_URL deve apontar somente para a origem pública do Keycloak.');
  }

  return {
    clientId,
    emissor: `${urlKeycloak.origin}/realms/${REALM_KEYCLOAK}`,
  };
}
