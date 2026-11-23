import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ProvedorAutenticacao, useAutenticacao } from '../autenticacao';
import { EstadoFeedback } from '../componentes';
import type { LinkAcompanharAgendamento } from '../servicos';
import { NavegacaoAbas } from './NavegacaoAbas';
import { AcompanhamentoSaga, Login } from '../telas';
import { cores } from '../tema';

export type ParametrosRaiz = {
  Abas: undefined;
  AcompanhamentoSaga: { linkAcompanhar?: LinkAcompanharAgendamento } | undefined;
};

const PilhaRaiz = createNativeStackNavigator<ParametrosRaiz>();

export function NavegacaoPrincipal() {
  const autenticacao = useAutenticacao();

  return (
    <NavigationContainer>
      <ProvedorAutenticacao autenticacao={autenticacao}>
        {autenticacao.estado === 'RESTAURANDO' ? (
          <SafeAreaView style={estilos.areaSegura}>
            <View style={estilos.conteudo}>
              <EstadoFeedback descricao="Restaurando sua sessão segura." tipo="carregando" titulo="Aguarde" />
            </View>
          </SafeAreaView>
        ) : autenticacao.estado === 'AUTENTICADO' ? (
          <PilhaRaiz.Navigator screenOptions={{ headerShown: false }}>
            <PilhaRaiz.Screen component={NavegacaoAbas} name="Abas" />
            <PilhaRaiz.Screen component={AcompanhamentoSaga} name="AcompanhamentoSaga" />
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

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { flex: 1, justifyContent: 'center' },
});
