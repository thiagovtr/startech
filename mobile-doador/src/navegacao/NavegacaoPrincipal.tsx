import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ProvedorAutenticacao, useAutenticacao } from '../autenticacao';
import { EstadoFeedback } from '../componentes';
import {
  consultarHome,
  ErroHttp,
  type CampanhaHome,
  type LinkAcompanharAgendamento,
  type LinkConsultarAgendamento,
  type SlotDisponivel,
} from '../servicos';
import { NavegacaoAbas } from './NavegacaoAbas';
import {
  AcompanhamentoSaga,
  CadastroPerfil,
  CompletarPerfil,
  DetalhesAgendamento,
  InformacoesBasicas,
  Login,
  Perfil,
  Seguranca,
  TodasCampanhas,
  TodosHorarios,
  ResumoAgendamento,
  TodosPedidosAnteriores,
} from '../telas';
import { cores } from '../tema';

export type ParametrosRaiz = {
  Abas: undefined;
  AcompanhamentoSaga: { linkAcompanhar?: LinkAcompanharAgendamento } | undefined;
  DetalhesAgendamento: { linkConsultar: LinkConsultarAgendamento };
  Perfil: undefined;
  InformacoesBasicas: { nome?: string } | undefined;
  Seguranca: undefined;
  CadastroPerfil: { tipoSanguineo?: string } | undefined;
  TodasCampanhas: { campanhas: CampanhaHome[]; campanhasPersonalizadas: boolean };
  TodosHorarios: { slots: SlotDisponivel[] };
  ResumoAgendamento: { slot: SlotDisponivel };
  TodosPedidosAnteriores: undefined;
};

const PilhaRaiz = createNativeStackNavigator<ParametrosRaiz>();

type EstadoPerfil = 'NAO_VERIFICADO' | 'CARREGANDO' | 'CADASTRADO' | 'PENDENTE' | 'ERRO';

export function NavegacaoPrincipal() {
  const autenticacao = useAutenticacao();
  const [estadoPerfil, definirEstadoPerfil] = useState<EstadoPerfil>('NAO_VERIFICADO');
  const [mensagemErroPerfil, definirMensagemErroPerfil] = useState('');
  const [clienteVerificado, definirClienteVerificado] = useState<typeof autenticacao.clienteHttp | null>(null);

  const verificarPerfil = useCallback(async (signal?: AbortSignal) => {
    const clienteAtual = autenticacao.clienteHttp;
    definirEstadoPerfil('CARREGANDO');
    definirMensagemErroPerfil('');

    try {
      const home = await consultarHome(clienteAtual, signal);

      if (signal?.aborted) return;

      const perfilPendente = home.doador.cadastrado === false && !home.doador.statusDegradado;
      definirClienteVerificado(clienteAtual);
      definirEstadoPerfil(perfilPendente ? 'PENDENTE' : 'CADASTRADO');
    } catch (erro) {
      if (signal?.aborted) return;

      definirClienteVerificado(clienteAtual);
      definirEstadoPerfil('ERRO');
      definirMensagemErroPerfil(obterMensagemErroPerfil(erro));
    }
  }, [autenticacao.clienteHttp]);

  useEffect(() => {
    if (autenticacao.estado !== 'AUTENTICADO') {
      definirEstadoPerfil('NAO_VERIFICADO');
      definirMensagemErroPerfil('');
      definirClienteVerificado(null);
      return;
    }

    const controlador = new AbortController();
    void verificarPerfil(controlador.signal);

    return () => controlador.abort();
  }, [autenticacao.estado, verificarPerfil]);

  const perfilDaSessaoAtualFoiVerificado = clienteVerificado === autenticacao.clienteHttp;

  return (
    <NavigationContainer>
      <ProvedorAutenticacao autenticacao={autenticacao}>
        {autenticacao.estado === 'RESTAURANDO' ? (
          <SafeAreaView style={estilos.areaSegura}>
            <View style={estilos.conteudo}>
              <EstadoFeedback descricao="Restaurando sua sessão segura." tipo="carregando" titulo="Aguarde" />
            </View>
          </SafeAreaView>
        ) : autenticacao.estado === 'AUTENTICADO' && (!perfilDaSessaoAtualFoiVerificado || estadoPerfil === 'NAO_VERIFICADO' || estadoPerfil === 'CARREGANDO') ? (
          <TelaCarregamentoPerfil />
        ) : autenticacao.estado === 'AUTENTICADO' && estadoPerfil === 'ERRO' ? (
          <TelaErroPerfil
            aoTentarNovamente={() => void verificarPerfil()}
            mensagem={mensagemErroPerfil}
          />
        ) : autenticacao.estado === 'AUTENTICADO' && estadoPerfil === 'PENDENTE' ? (
          <CompletarPerfil aoConcluir={() => void verificarPerfil()} />
        ) : autenticacao.estado === 'AUTENTICADO' ? (
          <PilhaRaiz.Navigator screenOptions={{ headerShown: false }}>
            <PilhaRaiz.Screen component={NavegacaoAbas} name="Abas" />
            <PilhaRaiz.Screen component={AcompanhamentoSaga} name="AcompanhamentoSaga" />
            <PilhaRaiz.Screen component={DetalhesAgendamento} name="DetalhesAgendamento" />
            <PilhaRaiz.Screen component={Perfil} name="Perfil" />
            <PilhaRaiz.Screen component={InformacoesBasicas} name="InformacoesBasicas" />
            <PilhaRaiz.Screen component={Seguranca} name="Seguranca" />
            <PilhaRaiz.Screen component={CadastroPerfil} name="CadastroPerfil" />
            <PilhaRaiz.Screen component={TodasCampanhas} name="TodasCampanhas" />
            <PilhaRaiz.Screen component={TodosHorarios} name="TodosHorarios" />
            <PilhaRaiz.Screen component={ResumoAgendamento} name="ResumoAgendamento" />
            <PilhaRaiz.Screen component={TodosPedidosAnteriores} name="TodosPedidosAnteriores" />
          </PilhaRaiz.Navigator>
        ) : (
          <Login
            aoEntrar={() => void autenticacao.iniciarLogin()}
            carregando={autenticacao.carregandoLogin}
            desabilitado={autenticacao.estado === 'ERRO'}
            mensagemErro={autenticacao.mensagemErro}
          />
        )}
      </ProvedorAutenticacao>
    </NavigationContainer>
  );
}

function TelaCarregamentoPerfil() {
  return (
    <SafeAreaView style={estilos.areaSegura}>
      <View style={estilos.conteudo}>
        <EstadoFeedback descricao="Verificando as informações do seu perfil." tipo="carregando" titulo="Aguarde" />
      </View>
    </SafeAreaView>
  );
}

function TelaErroPerfil({ aoTentarNovamente, mensagem }: { aoTentarNovamente: () => void; mensagem: string }) {
  return (
    <SafeAreaView style={estilos.areaSegura}>
      <View style={estilos.conteudo}>
        <EstadoFeedback
          aoTentarNovamente={aoTentarNovamente}
          descricao={mensagem}
          tipo="erro"
          titulo="Não foi possível verificar seu perfil"
        />
      </View>
    </SafeAreaView>
  );
}

function obterMensagemErroPerfil(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    return erro.problema.detail ?? erro.problema.title;
  }

  return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { flex: 1, justifyContent: 'center' },
});
