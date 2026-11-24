import * as AuthSession from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { obterConfiguracaoOidc, type ConfiguracaoOidc } from '../configuracao';
import { criarClienteHttp } from '../servicos';
import {
  limparSessaoArmazenada,
  obterSessaoArmazenada,
  salvarSessaoArmazenada,
  type SessaoAutenticada,
} from './armazenamentoSessao';

WebBrowser.maybeCompleteAuthSession();

export type EstadoAutenticacao = 'RESTAURANDO' | 'ANONIMO' | 'AUTENTICADO' | 'ERRO';

export type Autenticacao = ReturnType<typeof useAutenticacao>;

type ResultadoConfiguracao = {
  configuracao?: ConfiguracaoOidc;
  erro?: string;
};

function lerConfiguracao(): ResultadoConfiguracao {
  try {
    return { configuracao: obterConfiguracaoOidc() };
  } catch (erro) {
    return { erro: erro instanceof Error ? erro.message : 'Não foi possível carregar a configuração de autenticação.' };
  }
}

export function useAutenticacao() {
  const [resultadoConfiguracao] = useState<ResultadoConfiguracao>(lerConfiguracao);
  const configuracao = resultadoConfiguracao.configuracao;
  const uriRedirecionamento =
    process.env.EXPO_PUBLIC_REDIRECT_URI?.trim()
    || AuthSession.makeRedirectUri({ scheme: 'startech', path: 'autenticacao' });
  const [descoberta, definirDescoberta] = useState<AuthSession.DiscoveryDocument | null>(null);
  const [requisicao, , solicitarAutorizacao] = AuthSession.useAuthRequest(
    {
      clientId: configuracao?.clientId ?? 'configuracao-invalida',
      redirectUri: uriRedirecionamento,
      responseType: AuthSession.ResponseType.Code,
      scopes: ['openid'],
      usePKCE: true,
    },
    descoberta,
  );
  const [estado, definirEstado] = useState<EstadoAutenticacao>(resultadoConfiguracao.erro ? 'ERRO' : 'RESTAURANDO');
  const [sessao, definirSessao] = useState<SessaoAutenticada | null>(null);
  const [mensagemErro, definirMensagemErro] = useState(resultadoConfiguracao.erro ?? '');
  const [carregandoLogin, definirCarregandoLogin] = useState(false);

  useEffect(() => {
    if (!configuracao) {
      return;
    }

    const configuracaoAtual = configuracao;
    let ativa = true;

    async function carregarDescoberta() {
      try {
        const documentoDescoberta = await AuthSession.fetchDiscoveryAsync(configuracaoAtual.emissor);
        if (ativa) {
          definirDescoberta(documentoDescoberta);
        }
      } catch {
        if (ativa) {
          definirEstado('ANONIMO');
          definirMensagemErro('Não foi possível acessar a configuração do Keycloak. Verifique a conexão e tente novamente.');
        }
      }
    }

    void carregarDescoberta();

    return () => {
      ativa = false;
    };
  }, [configuracao]);

  const atualizarSessao = useCallback(async (sessaoAtual: SessaoAutenticada): Promise<SessaoAutenticada> => {
    if (!configuracao || !descoberta || !sessaoAtual.refreshToken || !tokenPrecisaRenovar(sessaoAtual)) {
      return sessaoAtual;
    }

    const respostaToken = await AuthSession.refreshAsync(
      { clientId: configuracao.clientId, refreshToken: sessaoAtual.refreshToken },
      descoberta,
    );
    const sessaoRenovada = criarSessao(respostaToken, sessaoAtual.refreshToken);
    await salvarSessaoArmazenada(sessaoRenovada);
    return sessaoRenovada;
  }, [configuracao, descoberta]);

  useEffect(() => {
    if (!configuracao || !descoberta) {
      return;
    }

    let ativa = true;

    async function restaurarSessao() {
      try {
        const sessaoArmazenada = await obterSessaoArmazenada();
        const sessaoValida = sessaoArmazenada ? await atualizarSessao(sessaoArmazenada) : null;

        if (!ativa) return;

        definirSessao(sessaoValida);
        definirEstado(sessaoValida ? 'AUTENTICADO' : 'ANONIMO');
      } catch {
        await limparSessaoArmazenada();
        if (ativa) {
          definirSessao(null);
          definirEstado('ANONIMO');
          definirMensagemErro('Sua sessão expirou. Faça login novamente.');
        }
      }
    }

    void restaurarSessao();

    return () => {
      ativa = false;
    };
  }, [atualizarSessao, configuracao, descoberta]);

  const iniciarLogin = useCallback(async () => {
    if (!configuracao || !descoberta || !requisicao) {
      definirMensagemErro(resultadoConfiguracao.erro ?? 'O login ainda está sendo preparado. Tente novamente em instantes.');
      return;
    }

    definirCarregandoLogin(true);
    definirMensagemErro('');

    try {
      const resultado = await solicitarAutorizacao();

      if (resultado.type === 'cancel' || resultado.type === 'dismiss') {
        definirMensagemErro('Login cancelado. Você pode tentar novamente quando quiser.');
        return;
      }

      if (resultado.type !== 'success' || !resultado.params.code || !requisicao.codeVerifier) {
        definirMensagemErro('Não foi possível concluir o login. Tente novamente.');
        return;
      }

      const respostaToken = await AuthSession.exchangeCodeAsync(
        {
          clientId: configuracao.clientId,
          code: resultado.params.code,
          extraParams: { code_verifier: requisicao.codeVerifier },
          redirectUri: uriRedirecionamento,
        },
        descoberta,
      );
      const novaSessao = criarSessao(respostaToken);
      await salvarSessaoArmazenada(novaSessao);
      definirSessao(novaSessao);
      definirEstado('AUTENTICADO');
    } catch {
      definirMensagemErro('Não foi possível autenticar. Verifique a conexão e tente novamente.');
    } finally {
      definirCarregandoLogin(false);
    }
  }, [configuracao, descoberta, requisicao, resultadoConfiguracao.erro, solicitarAutorizacao, uriRedirecionamento]);

  const encerrarSessao = useCallback(async () => {
    try {
      if (configuracao && descoberta?.revocationEndpoint && sessao?.refreshToken) {
        await AuthSession.revokeAsync(
          { clientId: configuracao.clientId, token: sessao.refreshToken },
          descoberta,
        );
      }
    } catch {
      definirMensagemErro('A sessão foi encerrada neste aparelho, mas o Keycloak não confirmou a revogação do token.');
    } finally {
      try {
        await limparSessaoArmazenada();
      } catch {
        definirMensagemErro('Não foi possível remover os dados locais da sessão. Faça login novamente apenas após confirmar a limpeza do aparelho.');
      } finally {
        definirSessao(null);
        definirEstado('ANONIMO');
      }
    }
  }, [configuracao, descoberta, sessao]);

  const obterTokenAcesso = useCallback(async (): Promise<string | null> => {
    const sessaoArmazenada = sessao ?? await obterSessaoArmazenada();

    if (!sessaoArmazenada) {
      return null;
    }

    try {
      const sessaoValida = await atualizarSessao(sessaoArmazenada);
      definirSessao(sessaoValida);
      return sessaoValida.accessToken;
    } catch {
      await encerrarSessao();
      return null;
    }
  }, [atualizarSessao, encerrarSessao, sessao]);

  const clienteHttp = useMemo(() => criarClienteHttp(obterTokenAcesso), [obterTokenAcesso]);

  return {
    carregandoLogin,
    clienteHttp,
    encerrarSessao,
    estado,
    iniciarLogin,
    mensagemErro,
    sessao,
  };
}

function criarSessao(respostaToken: AuthSession.TokenResponse, refreshTokenAnterior?: string): SessaoAutenticada {
  return {
    accessToken: respostaToken.accessToken,
    expiresIn: respostaToken.expiresIn,
    issuedAt: respostaToken.issuedAt ?? Math.floor(Date.now() / 1000),
    refreshToken: respostaToken.refreshToken ?? refreshTokenAnterior,
  };
}

function tokenPrecisaRenovar(sessao: SessaoAutenticada): boolean {
  if (!sessao.expiresIn) {
    return false;
  }

  const expiracaoComMargem = sessao.issuedAt + sessao.expiresIn - 60;
  return Math.floor(Date.now() / 1000) >= expiracaoComMargem;
}
