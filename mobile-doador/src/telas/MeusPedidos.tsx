import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { Cartao, EstadoFeedback, SeloStatus, type SituacaoSelo } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, listarAgendamentos, type Agendamento, type SituacaoAgendamento } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type EstadoLista = 'CARREGANDO' | 'SUCESSO' | 'ERRO';

export function MeusPedidos() {
  const { clienteHttp } = useContextoAutenticacao();
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const [estadoLista, definirEstadoLista] = useState<EstadoLista>('CARREGANDO');
  const [agendamentos, definirAgendamentos] = useState<Agendamento[]>([]);
  const [mensagemErro, definirMensagemErro] = useState('');

  const carregarAgendamentos = useCallback(async () => {
    definirEstadoLista('CARREGANDO');
    definirMensagemErro('');

    try {
      const resposta = await listarAgendamentos(clienteHttp);
      definirAgendamentos(resposta.itens);
      definirEstadoLista('SUCESSO');
    } catch (erro) {
      definirAgendamentos([]);
      definirMensagemErro(obterMensagemErro(erro));
      definirEstadoLista('ERRO');
    }
  }, [clienteHttp]);

  useFocusEffect(useCallback(() => {
    void carregarAgendamentos();
  }, [carregarAgendamentos]));

  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Meus pedidos</Text>
          <Text style={estilos.descricao}>Consulte seus agendamentos e acompanhe a situação de cada um.</Text>
        </View>

        <Pressable
          accessibilityLabel="Atualizar meus agendamentos"
          accessibilityRole="button"
          disabled={estadoLista === 'CARREGANDO'}
          onPress={() => void carregarAgendamentos()}
          style={({ pressed }) => [estilos.acaoAtualizar, pressed && estilos.acaoAtualizarPressionada]}
        >
          <Text style={estilos.textoAtualizar}>Atualizar agendamentos</Text>
        </Pressable>

        {estadoLista === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Consultando agendamentos" />}
        {estadoLista === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => void carregarAgendamentos()}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível consultar agendamentos"
          />
        )}
        {estadoLista === 'SUCESSO' && agendamentos.length === 0 && (
          <EstadoFeedback
            descricao="Você não possui agendamentos para exibir no momento."
            tipo="vazio"
            titulo="Nenhum agendamento encontrado"
          />
        )}
        {estadoLista === 'SUCESSO' && agendamentos.length > 0 && (
          <View style={estilos.lista}>
            {agendamentos.map((agendamento) => (
              <CartaoAgendamento
                agendamento={agendamento}
                aoAbrir={() => navegacao.navigate('DetalhesAgendamento', { linkConsultar: agendamento._links.self })}
                key={agendamento.id}
              />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function CartaoAgendamento({ agendamento, aoAbrir }: { agendamento: Agendamento; aoAbrir: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Abrir agendamento no posto ${agendamento.slot.postoId}`}
      onPress={aoAbrir}
      style={({ pressed }) => [estilos.cartaoPressionavel, pressed && estilos.cartaoPressionado]}
    >
      <Cartao estilo={estilos.cartaoAgendamento}>
        <View style={estilos.linhaCartao}>
          <Text style={estilos.nomePosto}>Posto: {agendamento.slot.postoId}</Text>
          <SeloStatus situacao={obterSelo(agendamento.status)} />
        </View>
        <Text style={estilos.periodo}>{formatarPeriodo(agendamento)}</Text>
        <Text style={estilos.abrirDetalhes}>Ver detalhes</Text>
      </Cartao>
    </Pressable>
  );
}

function obterSelo(situacao: SituacaoAgendamento): SituacaoSelo {
  if (situacao === 'CONFIRMADO') return 'CONFIRMADO';
  if (situacao === 'CANCELADO_DOADOR' || situacao === 'CANCELADO_COMPENSACAO_SAGA') return 'CANCELADO';
  return 'PENDENTE';
}

function formatarPeriodo(agendamento: Agendamento): string {
  const inicio = new Date(agendamento.slot.dataHoraInicio);
  const fim = new Date(agendamento.slot.dataHoraFim);
  if (Number.isNaN(inicio.getTime()) || Number.isNaN(fim.getTime())) return 'Período indisponível para exibição.';

  const data = inicio.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', weekday: 'long' });
  const horarioInicio = inicio.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const horarioFim = fim.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${data} · ${horarioInicio} às ${horarioFim}`;
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para consultar seus agendamentos.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'O serviço de agendamentos está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }

  return erro instanceof Error ? erro.message : 'Não foi possível consultar os agendamentos. Tente novamente.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  acaoAtualizar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  acaoAtualizarPressionada: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media },
  textoAtualizar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  lista: { gap: espacamentos.medio },
  cartaoPressionavel: { borderRadius: raiosBorda.media },
  cartaoPressionado: { opacity: 0.82 },
  cartaoAgendamento: { gap: espacamentos.pequeno },
  linhaCartao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  nomePosto: { color: cores.texto, flex: 1, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  periodo: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  abrirDetalhes: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
});
