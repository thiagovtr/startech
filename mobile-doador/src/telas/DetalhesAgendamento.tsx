import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useCallback, useRef, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { Cartao, EstadoFeedback, SeloStatus, type SituacaoSelo } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cancelarAgendamento, consultarAgendamento, ErroHttp, type Agendamento, type SituacaoAgendamento } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type EstadoDetalhes = 'CARREGANDO' | 'SUCESSO' | 'ERRO';

export function DetalhesAgendamento() {
  const { clienteHttp } = useContextoAutenticacao();
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'DetalhesAgendamento'>>();
  const [estadoDetalhes, definirEstadoDetalhes] = useState<EstadoDetalhes>('CARREGANDO');
  const [agendamento, definirAgendamento] = useState<Agendamento>();
  const [mensagemErro, definirMensagemErro] = useState('');
  const [tentativa, definirTentativa] = useState(0);
  const [cancelando, definirCancelando] = useState(false);
  const [mensagemCancelamento, definirMensagemCancelamento] = useState('');
  const cancelamentoEmAndamento = useRef(false);

  useFocusEffect(useCallback(() => {
    const controlador = new AbortController();
    let telaAtiva = true;

    async function carregarDetalhes() {
      definirEstadoDetalhes('CARREGANDO');
      definirMensagemErro('');

      try {
        const resposta = await consultarAgendamento(clienteHttp, rota.params.linkConsultar, controlador.signal);
        if (!telaAtiva) return;
        definirAgendamento(resposta);
        definirEstadoDetalhes('SUCESSO');
      } catch (erro) {
        if (!telaAtiva) return;
        definirAgendamento(undefined);
        definirMensagemErro(obterMensagemErro(erro));
        definirEstadoDetalhes('ERRO');
      }
    }

    void carregarDetalhes();
    return () => {
      telaAtiva = false;
      controlador.abort();
    };
  }, [clienteHttp, rota.params.linkConsultar, tentativa]));

  function confirmarCancelamento() {
    if (!agendamento?._links.cancelar || cancelamentoEmAndamento.current) return;

    Alert.alert(
      'Cancelar agendamento',
      'Deseja cancelar este agendamento? Esta ação só será enviada após sua confirmação.',
      [
        { style: 'cancel', text: 'Manter agendamento' },
        {
          text: 'Cancelar agendamento',
          onPress: () => void executarCancelamento(agendamento._links.cancelar!),
        },
      ],
    );
  }

  async function executarCancelamento(linkCancelar: NonNullable<Agendamento['_links']['cancelar']>) {
    if (cancelamentoEmAndamento.current) return;

    cancelamentoEmAndamento.current = true;
    definirCancelando(true);
    definirMensagemCancelamento('');

    try {
      const resposta = await cancelarAgendamento(clienteHttp, linkCancelar);
      definirAgendamento(resposta);
      definirMensagemCancelamento('Agendamento cancelado. As informações abaixo foram atualizadas.');
    } catch (erro) {
      definirMensagemCancelamento(obterMensagemErroCancelamento(erro));
      if (erro instanceof ErroHttp && erro.categoria === 'CONFLITO') {
        definirTentativa((valor) => valor + 1);
      }
    } finally {
      cancelamentoEmAndamento.current = false;
      definirCancelando(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para Meus pedidos" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Detalhes do agendamento</Text>
          <Text style={estilos.descricao}>Confira as informações retornadas para este agendamento.</Text>
        </View>

        {estadoDetalhes === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Consultando agendamento" />}
        {estadoDetalhes === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => definirTentativa((valor) => valor + 1)}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível consultar o agendamento"
          />
        )}
        {estadoDetalhes === 'SUCESSO' && agendamento && (
          <ConteudoAgendamento
            agendamento={agendamento}
            aoCancelar={confirmarCancelamento}
            cancelando={cancelando}
            mensagemCancelamento={mensagemCancelamento}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

type PropriedadesConteudoAgendamento = {
  agendamento: Agendamento;
  cancelando: boolean;
  mensagemCancelamento: string;
  aoCancelar: () => void;
};

function ConteudoAgendamento({ agendamento, cancelando, mensagemCancelamento, aoCancelar }: PropriedadesConteudoAgendamento) {
  return (
    <>
      <Cartao estilo={estilos.cartao}>
        <View style={estilos.linhaCartao}>
          <View style={estilos.detalhesPrincipais}>
            <Text style={estilos.rotulo}>Posto</Text>
            <Text style={estilos.valorPrincipal}>{agendamento.slot.postoId}</Text>
          </View>
          <View style={estilos.iconeStatus}>
            <Ionicons color={cores.principalEscuro} name="calendar-outline" size={20} />
          </View>
          <SeloStatus situacao={obterSelo(agendamento.status)} />
        </View>
        <Informacao rotulo="Data e horário" valor={formatarPeriodo(agendamento)} />
        <Informacao rotulo="Situação" valor={formatarSituacao(agendamento.status)} />
        <Informacao rotulo="Identificador" valor={agendamento.id} />
        {agendamento.concluido && <Informacao rotulo="Atendimento" valor="Horário encerrado" />}
      </Cartao>

      {agendamento.disclaimerLegal && (
        <Cartao estilo={estilos.cartaoInformativo}>
          <Text style={estilos.rotulo}>Informação importante</Text>
          <Text style={estilos.textoInformativo}>{agendamento.disclaimerLegal}</Text>
        </Cartao>
      )}

      {(agendamento.dataCancelamento || agendamento.motivo || agendamento.slotLiberado) && (
        <Cartao estilo={estilos.cartaoInformativo}>
          <Text style={estilos.rotulo}>Informações de cancelamento</Text>
          {agendamento.dataCancelamento && <Informacao rotulo="Data do cancelamento" valor={formatarData(agendamento.dataCancelamento)} />}
          {agendamento.motivo && <Informacao rotulo="Motivo" valor={agendamento.motivo} />}
          {agendamento.slotLiberado && <Informacao rotulo="Slot liberado" valor={agendamento.slotLiberado} />}
        </Cartao>
      )}

      {mensagemCancelamento && <Text style={estilos.mensagemCancelamento}>{mensagemCancelamento}</Text>}

      {agendamento._links.cancelar && (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ busy: cancelando, disabled: cancelando }}
          disabled={cancelando}
          onPress={aoCancelar}
          style={({ pressed }) => [
            estilos.botaoCancelar,
            cancelando && estilos.botaoCancelarDesabilitado,
            pressed && !cancelando && estilos.botaoCancelarPressionado,
          ]}
        >
          <Text style={estilos.textoBotaoCancelar}>{cancelando ? 'Cancelando agendamento...' : 'Cancelar agendamento'}</Text>
        </Pressable>
      )}
    </>
  );
}

function Informacao({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <View style={estilos.informacao}>
      <Text style={estilos.rotulo}>{rotulo}</Text>
      <Text style={estilos.valor}>{valor}</Text>
    </View>
  );
}

function obterSelo(situacao: SituacaoAgendamento): SituacaoSelo {
  if (situacao === 'CONFIRMADO') return 'CONFIRMADO';
  if (situacao === 'CANCELADO_DOADOR' || situacao === 'CANCELADO_COMPENSACAO_SAGA') return 'CANCELADO';
  return 'PENDENTE';
}

function formatarSituacao(situacao: SituacaoAgendamento): string {
  const descricoes: Record<SituacaoAgendamento, string> = {
    CRIADO_PROVISORIO: 'Em processamento',
    CONFIRMADO: 'Confirmado',
    CANCELADO_DOADOR: 'Cancelado pelo doador',
    CANCELADO_COMPENSACAO_SAGA: 'Cancelado durante o processamento',
  };
  return descricoes[situacao];
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

function formatarData(valor: string): string {
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleString('pt-BR', { dateStyle: 'medium', timeStyle: 'short' });
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para consultar o agendamento.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'O serviço de agendamentos está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }
  return erro instanceof Error ? erro.message : 'Não foi possível consultar os detalhes. Tente novamente.';
}

function obterMensagemErroCancelamento(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'CONFLITO') {
      return erro.problema.detail ?? 'O agendamento não pode mais ser cancelado. As informações foram atualizadas.';
    }
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para cancelar o agendamento.';
    if (erro.categoria === 'NAO_ENCONTRADO') return 'Este agendamento não foi encontrado para a sua conta.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'O cancelamento está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }
  return erro instanceof Error ? erro.message : 'Não foi possível cancelar o agendamento. Tente novamente.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartao: { gap: espacamentos.medio, padding: espacamentos.medio },
  cartaoInformativo: { backgroundColor: cores.principalClaro, gap: espacamentos.pequeno, padding: espacamentos.medio },
  linhaCartao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesPrincipais: { flex: 1, gap: espacamentos.minimo },
  iconeStatus: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, height: 36, justifyContent: 'center', width: 36 },
  rotulo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  valorPrincipal: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  informacao: { gap: espacamentos.minimo },
  valor: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 23 },
  textoInformativo: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  mensagemCancelamento: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio, lineHeight: 20 },
  botaoCancelar: { alignItems: 'center', backgroundColor: cores.principalEscuro, borderRadius: raiosBorda.media, justifyContent: 'center', minHeight: 48, paddingHorizontal: espacamentos.grande, paddingVertical: espacamentos.medio },
  botaoCancelarDesabilitado: { backgroundColor: cores.principalClaro },
  botaoCancelarPressionado: { opacity: 0.86 },
  textoBotaoCancelar: { color: cores.cartao, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
});
