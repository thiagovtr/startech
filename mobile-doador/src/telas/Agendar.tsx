import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { CompositeNavigationProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao, EstadoFeedback } from '../componentes';
import type { ParametrosAbas } from '../navegacao/NavegacaoAbas';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, listarSlotsDisponiveis, solicitarAgendamento, type SlotDisponivel } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type EstadoDisponibilidade = 'CARREGANDO' | 'SUCESSO' | 'ERRO';
type NavegacaoAgendar = CompositeNavigationProp<
  BottomTabNavigationProp<ParametrosAbas>,
  NativeStackNavigationProp<ParametrosRaiz>
>;

export function Agendar() {
  const { clienteHttp } = useContextoAutenticacao();
  const navegacao = useNavigation<NavegacaoAgendar>();
  const [estadoDisponibilidade, definirEstadoDisponibilidade] = useState<EstadoDisponibilidade>('CARREGANDO');
  const [slots, definirSlots] = useState<SlotDisponivel[]>([]);
  const [slotSelecionado, definirSlotSelecionado] = useState<SlotDisponivel>();
  const [mensagemErro, definirMensagemErro] = useState('');
  const [enviandoSolicitacao, definirEnviandoSolicitacao] = useState(false);

  const carregarSlots = useCallback(async (preservarMensagemErro = false) => {
    definirEstadoDisponibilidade('CARREGANDO');
    if (!preservarMensagemErro) definirMensagemErro('');

    try {
      const resposta = await listarSlotsDisponiveis(clienteHttp);
      definirSlots(resposta.itens);
      definirSlotSelecionado((selecionado) => resposta.itens.find((slot) => slot.slotId === selecionado?.slotId));
      definirEstadoDisponibilidade('SUCESSO');
    } catch (erro) {
      definirSlots([]);
      definirSlotSelecionado(undefined);
      definirMensagemErro(obterMensagemErroDisponibilidade(erro));
      definirEstadoDisponibilidade('ERRO');
    }
  }, [clienteHttp]);

  useFocusEffect(useCallback(() => {
    void carregarSlots();
  }, [carregarSlots]));

  async function confirmarSolicitacao() {
    if (!slotSelecionado || enviandoSolicitacao) return;

    definirEnviandoSolicitacao(true);
    definirMensagemErro('');

    try {
      const resposta = await solicitarAgendamento(
        clienteHttp,
        { slotId: slotSelecionado.slotId },
        slotSelecionado._links.agendar,
      );
      navegacao.navigate('AcompanhamentoSaga', { linkAcompanhar: resposta._links.acompanhar });
    } catch (erro) {
      definirMensagemErro(obterMensagemErroSolicitacao(erro));
      if (erro instanceof ErroHttp && erro.categoria === 'CONFLITO') {
        void carregarSlots(true);
      }
    } finally {
      definirEnviandoSolicitacao(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Agendar doação</Text>
          <Text style={estilos.descricao}>Consulte os horários disponíveis e escolha o mais adequado para você.</Text>
        </View>

        <Pressable
          accessibilityLabel="Ir para Meus pedidos"
          accessibilityRole="button"
          onPress={() => navegacao.navigate('MeusPedidos')}
          style={({ pressed }) => [estilos.bannerPedidos, pressed && estilos.bannerPedidosPressionado]}
        >
          <View style={estilos.iconeBannerPedidos}>
            <Ionicons color={cores.principalEscuro} name="clipboard-outline" size={22} />
          </View>
          <View style={estilos.detalhesBannerPedidos}>
            <Text style={estilos.tituloBannerPedidos}>Acompanhe seus agendamentos</Text>
            <Text style={estilos.descricaoBannerPedidos}>Veja a situação dos seus pedidos e os detalhes de cada um.</Text>
          </View>
          <Text accessibilityElementsHidden style={estilos.setaBannerPedidos}>›</Text>
        </Pressable>

        <View style={estilos.linhaTituloSecao}>
          <Text style={estilos.tituloSecao}>Horários disponíveis</Text>
          <Pressable
            accessibilityLabel="Atualizar horários disponíveis"
            accessibilityRole="button"
            disabled={estadoDisponibilidade === 'CARREGANDO' || enviandoSolicitacao}
            onPress={() => void carregarSlots()}
            style={({ pressed }) => [estilos.acaoAtualizar, pressed && estilos.acaoAtualizarPressionada]}
          >
            <Text style={estilos.textoAtualizar}>Atualizar</Text>
          </Pressable>
        </View>

        {estadoDisponibilidade === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Consultando horários" />}
        {estadoDisponibilidade === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => void carregarSlots()}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível consultar horários"
          />
        )}
        {estadoDisponibilidade === 'SUCESSO' && slots.length === 0 && (
          <EstadoFeedback
            descricao="Não há horários disponíveis no momento. Atualize a consulta mais tarde."
            tipo="vazio"
            titulo="Nenhum horário disponível"
          />
        )}
        {estadoDisponibilidade === 'SUCESSO' && slots.length > 0 && (
          <View style={estilos.listaSlots}>
            {slots.map((slot) => (
              <CartaoHorario
                aoSelecionar={() => definirSlotSelecionado(slot)}
                estaSelecionado={slotSelecionado?.slotId === slot.slotId}
                key={slot.slotId}
                slot={slot}
              />
            ))}
          </View>
        )}

        <Cartao estilo={estilos.resumo}>
          <Text style={estilos.tituloSecao}>Resumo da solicitação</Text>
          {slotSelecionado ? (
            <>
              <Text style={estilos.nomePosto}>Posto: {slotSelecionado.postoId}</Text>
              <Text style={estilos.textoSecundario}>{formatarPeriodo(slotSelecionado)}</Text>
              <Text style={estilos.textoSecundario}>{formatarVagas(slotSelecionado.vagasDisponiveis)}</Text>
            </>
          ) : (
            <Text style={estilos.textoSecundario}>Selecione um horário disponível para continuar.</Text>
          )}
          {mensagemErro && estadoDisponibilidade !== 'ERRO' && <Text style={estilos.erroSolicitacao}>{mensagemErro}</Text>}
          <BotaoPrimario
            aoPressionar={() => void confirmarSolicitacao()}
            carregando={enviandoSolicitacao}
            desabilitado={!slotSelecionado || estadoDisponibilidade !== 'SUCESSO'}
            titulo="Confirmar solicitação"
          />
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

type PropriedadesCartaoHorario = {
  slot: SlotDisponivel;
  estaSelecionado: boolean;
  aoSelecionar: () => void;
};

function CartaoHorario({ slot, estaSelecionado, aoSelecionar }: PropriedadesCartaoHorario) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: estaSelecionado }}
      onPress={aoSelecionar}
      style={({ pressed }) => [
        estilos.cartaoHorario,
        estaSelecionado && estilos.cartaoHorarioSelecionado,
        pressed && !estaSelecionado && estilos.cartaoHorarioPressionado,
      ]}
    >
      <Text style={[estilos.nomePosto, estaSelecionado && estilos.textoSelecionado]}>Posto: {slot.postoId}</Text>
      <Text style={[estilos.periodo, estaSelecionado && estilos.textoSelecionado]}>{formatarPeriodo(slot)}</Text>
      <Text style={[estilos.vagas, estaSelecionado && estilos.textoSelecionado]}>{formatarVagas(slot.vagasDisponiveis)}</Text>
    </Pressable>
  );
}

function formatarPeriodo(slot: Pick<SlotDisponivel, 'dataHoraInicio' | 'dataHoraFim'>): string {
  const inicio = new Date(slot.dataHoraInicio);
  const fim = new Date(slot.dataHoraFim);

  if (Number.isNaN(inicio.getTime()) || Number.isNaN(fim.getTime())) {
    return 'Período informado pelo serviço indisponível para exibição.';
  }

  const data = inicio.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', weekday: 'long' });
  const horarioInicio = inicio.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  const horarioFim = fim.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${data} · ${horarioInicio} às ${horarioFim}`;
}

function formatarVagas(vagasDisponiveis: number): string {
  return vagasDisponiveis === 1 ? '1 vaga disponível' : `${vagasDisponiveis} vagas disponíveis`;
}

function obterMensagemErroDisponibilidade(erro: unknown): string {
  if (erro instanceof ErroHttp) {
    if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para consultar horários.';
    if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
      return erro.problema.detail ?? 'A disponibilidade está temporariamente indisponível. Tente novamente.';
    }
    return erro.problema.detail ?? erro.problema.title;
  }

  return erro instanceof Error ? erro.message : 'Não foi possível consultar os horários. Tente novamente.';
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
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.gigante * 3 },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  bannerPedidos: { alignItems: 'center', backgroundColor: cores.cartao, borderRadius: raiosBorda.grande, flexDirection: 'row', gap: espacamentos.medio, padding: espacamentos.padrao },
  bannerPedidosPressionado: { opacity: 0.78 },
  iconeBannerPedidos: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, height: 44, justifyContent: 'center', width: 44 },
  detalhesBannerPedidos: { flex: 1, gap: espacamentos.minimo },
  tituloBannerPedidos: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  descricaoBannerPedidos: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  setaBannerPedidos: { color: cores.principalEscuro, fontSize: tamanhosFonte.cabecalho, fontWeight: pesosFonte.normal },
  linhaTituloSecao: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  tituloSecao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  acaoAtualizar: { justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  acaoAtualizarPressionada: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media },
  textoAtualizar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  listaSlots: { gap: espacamentos.medio },
  cartaoHorario: { backgroundColor: cores.cartao, borderRadius: raiosBorda.media, gap: espacamentos.pequeno, minHeight: 112, padding: espacamentos.padrao },
  cartaoHorarioSelecionado: { backgroundColor: cores.principal },
  cartaoHorarioPressionado: { backgroundColor: cores.principalClaro },
  nomePosto: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  periodo: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  vagas: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  textoSelecionado: { color: cores.cartao },
  resumo: { gap: espacamentos.medio },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  erroSolicitacao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
});
