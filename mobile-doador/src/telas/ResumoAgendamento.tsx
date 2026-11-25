import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, solicitarAgendamento, type SlotDisponivel } from '../servicos';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export function ResumoAgendamento() {
  const { clienteHttp } = useContextoAutenticacao();
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'ResumoAgendamento'>>();
  const { slot } = rota.params;
  const [enviandoSolicitacao, definirEnviandoSolicitacao] = useState(false);
  const [mensagemErro, definirMensagemErro] = useState('');

  async function confirmarSolicitacao() {
    if (enviandoSolicitacao) return;

    definirEnviandoSolicitacao(true);
    definirMensagemErro('');

    try {
      const resposta = await solicitarAgendamento(
        clienteHttp,
        { slotId: slot.slotId },
        slot._links.agendar,
      );
      navegacao.replace('AcompanhamentoSaga', { linkAcompanhar: resposta._links.acompanhar });
    } catch (erro) {
      definirMensagemErro(obterMensagemErroSolicitacao(erro));
    } finally {
      definirEnviandoSolicitacao(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para escolher outro horário" accessibilityRole="button" disabled={enviandoSolicitacao} onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Text style={estilos.textoVoltar}>← Escolher outro horário</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Resumo do agendamento</Text>
          <Text style={estilos.descricao}>Confira os dados antes de enviar sua solicitação.</Text>
        </View>

        <Cartao estilo={estilos.resumo}>
          <InformacaoRotulo rotulo="Posto" valor={slot.postoId} />
          <InformacaoRotulo rotulo="Data" valor={formatarData(slot.dataHoraInicio)} />
          <InformacaoRotulo rotulo="Horário" valor={formatarHorario(slot)} />
          <InformacaoRotulo rotulo="Disponibilidade" valor={formatarVagas(slot.vagasDisponiveis)} />
        </Cartao>

        {mensagemErro ? <Text style={estilos.erro}>{mensagemErro}</Text> : null}

        <BotaoPrimario
          aoPressionar={() => void confirmarSolicitacao()}
          carregando={enviandoSolicitacao}
          titulo="Confirmar solicitação"
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function InformacaoRotulo({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={estilos.linhaInformacao}>
      <Text style={estilos.rotulo}>{rotulo}</Text>
      <Text style={estilos.valor}>{valor}</Text>
    </View>
  );
}

function formatarData(dataHora: string): string {
  const data = new Date(dataHora);
  if (Number.isNaN(data.getTime())) return 'Data informada pelo serviço indisponível para exibição.';

  return data.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', weekday: 'long' });
}

function formatarHorario(slot: Pick<SlotDisponivel, 'dataHoraInicio' | 'dataHoraFim'>): string {
  const inicio = new Date(slot.dataHoraInicio);
  const fim = new Date(slot.dataHoraFim);
  if (Number.isNaN(inicio.getTime()) || Number.isNaN(fim.getTime())) return 'Horário informado pelo serviço indisponível para exibição.';

  const horarioInicio = inicio.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const horarioFim = fim.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${horarioInicio} às ${horarioFim}`;
}

function formatarVagas(vagasDisponiveis: number): string {
  return vagasDisponiveis === 1 ? '1 vaga disponível' : `${vagasDisponiveis} vagas disponíveis`;
}

function obterMensagemErroSolicitacao(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'CONFLITO') {
      return erro.problema.detail ?? 'Este horário não está mais disponível ou você já possui uma solicitação em andamento.';
    }
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para continuar.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'O agendamento está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }

  return erro instanceof Error ? erro.message : 'Não foi possível enviar a solicitação. Tente novamente.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  resumo: { gap: espacamentos.padrao },
  linhaInformacao: { gap: espacamentos.minimo },
  rotulo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valor: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  erro: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
});
