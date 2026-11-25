import { Ionicons } from '@expo/vector-icons';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { CompositeNavigationProp } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { EstadoFeedback } from '../componentes';
import type { ParametrosAbas } from '../navegacao/NavegacaoAbas';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, listarSlotsDisponiveis, type SlotDisponivel } from '../servicos';
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
  const [mensagemErro, definirMensagemErro] = useState('');

  const carregarSlots = useCallback(async () => {
    definirEstadoDisponibilidade('CARREGANDO');
    definirMensagemErro('');

    try {
      const resposta = await listarSlotsDisponiveis(clienteHttp);
      definirSlots(resposta.itens);
      definirEstadoDisponibilidade('SUCESSO');
    } catch (erro) {
      definirSlots([]);
      definirMensagemErro(obterMensagemErroDisponibilidade(erro));
      definirEstadoDisponibilidade('ERRO');
    }
  }, [clienteHttp]);

  useFocusEffect(useCallback(() => {
    void carregarSlots();
  }, [carregarSlots]));

  const horariosDaPrevia = slots.slice(0, 3);
  const haMaisHorarios = slots.length > horariosDaPrevia.length;

  return (
    <SafeAreaView edges={['top', 'right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Agendamentos</Text>
          <Text style={estilos.descricao}>Consulte horários e acompanhe suas solicitações de doação.</Text>
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
          <Ionicons accessibilityElementsHidden color={cores.principalEscuro} name="chevron-forward" size={20} />
        </Pressable>

        <View style={estilos.cabecalhoSecao}>
          <View style={estilos.detalhesSecao}>
            <Text style={estilos.tituloSecao}>Agendar doação</Text>
            <Text style={estilos.descricaoSecao}>Escolha um dos horários disponíveis para realizar sua doação de sangue.</Text>
          </View>
          <Pressable
            accessibilityLabel="Atualizar horários disponíveis"
            accessibilityRole="button"
            accessibilityState={{ busy: estadoDisponibilidade === 'CARREGANDO', disabled: estadoDisponibilidade === 'CARREGANDO' }}
            disabled={estadoDisponibilidade === 'CARREGANDO'}
            onPress={() => void carregarSlots()}
            style={({ pressed }) => [estilos.acaoAtualizar, pressed && estadoDisponibilidade !== 'CARREGANDO' && estilos.acaoAtualizarPressionada]}
          >
            {estadoDisponibilidade === 'CARREGANDO' ? (
              <ActivityIndicator color={cores.principalEscuro} size="small" />
            ) : (
              <Ionicons color={cores.principalEscuro} name="refresh" size={22} />
            )}
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
        {estadoDisponibilidade === 'SUCESSO' && horariosDaPrevia.length > 0 && (
          <View style={estilos.listaSlots}>
            {horariosDaPrevia.map((slot) => (
              <CartaoHorario
                aoSelecionar={() => navegacao.navigate('ResumoAgendamento', { slot })}
                key={slot.slotId}
                slot={slot}
              />
            ))}
            {haMaisHorarios && (
              <Pressable
                accessibilityLabel="Ver todos os horários disponíveis"
                accessibilityRole="button"
                onPress={() => navegacao.navigate('TodosHorarios', { slots })}
                style={({ pressed }) => [estilos.verTodos, pressed && estilos.verTodosPressionado]}
              >
                <Text style={estilos.textoVerTodos}>Ver todos</Text>
                <Ionicons color={cores.principalEscuro} name="arrow-forward" size={18} />
              </Pressable>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

type PropriedadesCartaoHorario = {
  slot: SlotDisponivel;
  aoSelecionar: () => void;
};

export function CartaoHorario({ slot, aoSelecionar }: PropriedadesCartaoHorario) {
  return (
    <Pressable
      accessibilityLabel={`Selecionar horário no posto ${slot.postoId}`}
      accessibilityRole="button"
      onPress={aoSelecionar}
      style={({ pressed }) => [estilos.cartaoHorario, pressed && estilos.cartaoHorarioPressionado]}
    >
      <Text style={estilos.nomePosto}>Posto: {slot.postoId}</Text>
      <Text style={estilos.periodo}>{formatarPeriodo(slot)}</Text>
      <Text style={estilos.vagas}>{formatarVagas(slot.vagasDisponiveis)}</Text>
    </Pressable>
  );
}

export function formatarPeriodo(slot: Pick<SlotDisponivel, 'dataHoraInicio' | 'dataHoraFim'>): string {
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

export function formatarVagas(vagasDisponiveis: number): string {
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
  cabecalhoSecao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.medio, justifyContent: 'space-between' },
  detalhesSecao: { flex: 1, gap: espacamentos.minimo },
  tituloSecao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  descricaoSecao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 22 },
  acaoAtualizar: { alignItems: 'center', backgroundColor: cores.principalClaro, borderRadius: raiosBorda.arredondada, height: 44, justifyContent: 'center', width: 44 },
  acaoAtualizarPressionada: { opacity: 0.72 },
  listaSlots: { gap: espacamentos.medio },
  cartaoHorario: { backgroundColor: cores.cartao, borderRadius: raiosBorda.media, gap: espacamentos.pequeno, minHeight: 112, padding: espacamentos.padrao },
  cartaoHorarioPressionado: { backgroundColor: cores.principalClaro },
  nomePosto: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  periodo: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal },
  vagas: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  verTodos: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  verTodosPressionado: { opacity: 0.72 },
  textoVerTodos: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
});
