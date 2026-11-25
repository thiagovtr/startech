import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { EstadoFeedback } from '../componentes';
import { CartaoAgendamento } from './MeusPedidos';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, listarAgendamentos, type Agendamento } from '../servicos';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

type EstadoLista = 'CARREGANDO' | 'SUCESSO' | 'ERRO';

export function TodosPedidosAnteriores() {
  const { clienteHttp } = useContextoAutenticacao();
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const [estadoLista, definirEstadoLista] = useState<EstadoLista>('CARREGANDO');
  const [anteriores, definirAnteriores] = useState<Agendamento[]>([]);
  const [mensagemErro, definirMensagemErro] = useState('');

  const carregarAnteriores = useCallback(async () => {
    definirEstadoLista('CARREGANDO');
    definirMensagemErro('');

    try {
      const resposta = await listarAgendamentos(clienteHttp);
      definirAnteriores(resposta.itens.filter((agendamento) => agendamento.status !== 'CONFIRMADO'));
      definirEstadoLista('SUCESSO');
    } catch (erro) {
      definirAnteriores([]);
      definirMensagemErro(obterMensagemErro(erro));
      definirEstadoLista('ERRO');
    }
  }, [clienteHttp]);

  useFocusEffect(useCallback(() => {
    void carregarAnteriores();
  }, [carregarAnteriores]));

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para Meus pedidos" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Pedidos anteriores</Text>
          <Text style={estilos.descricao}>Consulte seus pedidos que não estão confirmados.</Text>
        </View>

        {estadoLista === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Consultando pedidos" />}
        {estadoLista === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => void carregarAnteriores()}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível consultar pedidos"
          />
        )}
        {estadoLista === 'SUCESSO' && anteriores.length === 0 && (
          <EstadoFeedback
            descricao="Não há pedidos anteriores para exibir no momento."
            tipo="vazio"
            titulo="Nenhum pedido anterior"
          />
        )}
        {estadoLista === 'SUCESSO' && anteriores.length > 0 && (
          <View style={estilos.lista}>
            {anteriores.map((agendamento) => (
              <CartaoAgendamento
                agendamento={agendamento}
                aoAbrir={() => navegacao.navigate('DetalhesAgendamento', { linkConsultar: agendamento._links.self })}
                destaque={false}
                key={agendamento.id}
              />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para consultar seus pedidos.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'O serviço de agendamentos está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }

  return erro instanceof Error ? erro.message : 'Não foi possível consultar pedidos. Tente novamente.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.grande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  lista: { gap: espacamentos.medio, paddingTop: espacamentos.pequeno },
});
