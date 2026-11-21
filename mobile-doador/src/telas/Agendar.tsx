import { useState } from 'react';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao, SeloStatus } from '../componentes';
import type { ParametrosAbas } from '../navegacao/NavegacaoAbas';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { ErroHttp, solicitarAgendamento, slotIdEhValido, type RespostaSolicitacaoAgendamento } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type HorarioDemonstracao = {
  id: string;
  dia: string;
  horario: string;
};

// Dados temporários de interface; serão substituídos por horários retornados pela API.
const horariosDemonstracao: HorarioDemonstracao[] = [
  { id: 'horario-1', dia: 'Terça-feira', horario: '09:00' },
  { id: 'horario-2', dia: 'Terça-feira', horario: '10:30' },
  { id: 'horario-3', dia: 'Quarta-feira', horario: '14:00' },
  { id: 'horario-4', dia: 'Quinta-feira', horario: '15:30' },
];

export function Agendar() {
  const [horarioSelecionado, definirHorarioSelecionado] = useState<HorarioDemonstracao>();
  const [enviandoSolicitacao, definirEnviandoSolicitacao] = useState(false);
  const [erroSolicitacao, definirErroSolicitacao] = useState('');
  const [respostaSolicitacao, definirRespostaSolicitacao] = useState<RespostaSolicitacaoAgendamento>();
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosAbas, 'Agendar'>>();
  const { clienteHttp } = useContextoAutenticacao();
  const slotIdReal = rota.params?.slotIdReal;

  function confirmarDemonstracao() {
    Alert.alert(
      'Funcionalidade em demonstração',
      'A solicitação não foi enviada. O agendamento real será integrado em uma próxima etapa.',
    );
  }

  async function confirmarSolicitacaoReal() {
    if (!slotIdEhValido(slotIdReal)) {
      return;
    }

    definirEnviandoSolicitacao(true);
    definirErroSolicitacao('');

    try {
      const resposta = await solicitarAgendamento(clienteHttp, { slotId: slotIdReal });
      definirRespostaSolicitacao(resposta);
    } catch (erro) {
      definirRespostaSolicitacao(undefined);
      definirErroSolicitacao(obterMensagemErroSolicitacao(erro));
    } finally {
      definirEnviandoSolicitacao(false);
    }
  }

  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Agendar doação</Text>
          <Text style={estilos.descricao}>Escolha um horário demonstrativo para visualizar sua solicitação.</Text>
        </View>

        <Cartao estilo={estilos.cartaoCampanha}>
          <View style={estilos.linhaCartao}>
            <View style={estilos.detalhesCampanha}>
              <Text style={estilos.rotulo}>Campanha demonstrativa</Text>
              <Text style={estilos.nomeHemocentro}>Hemocentro Municipal</Text>
              <Text style={estilos.textoSecundario}>Tipo sanguíneo O+</Text>
            </View>
            <SeloStatus situacao="NORMAL" />
          </View>
          <Text style={estilos.avisoDemonstracao}>Informações apresentadas apenas para demonstração visual.</Text>
        </Cartao>

        <Cartao estilo={estilos.cartaoDisponibilidadeReal}>
          <Text style={estilos.tituloSecao}>Disponibilidade real</Text>
          {slotIdEhValido(slotIdReal) ? (
            <>
              <Text style={estilos.textoSecundario}>Um horário real foi recebido da API de disponibilidade.</Text>
              <BotaoPrimario
                aoPressionar={() => void confirmarSolicitacaoReal()}
                carregando={enviandoSolicitacao}
                titulo="Confirmar solicitação"
              />
              {respostaSolicitacao && (
                <View style={estilos.resultadoSolicitacao}>
                  <Text style={estilos.tituloResultado}>Solicitação recebida</Text>
                  <Text style={estilos.textoSecundario}>Situação: {respostaSolicitacao.situacao}</Text>
                  <Text style={estilos.textoSecundario}>Código da solicitação: {respostaSolicitacao.sagaId}</Text>
                  <Text style={estilos.textoSecundario}>Código do agendamento: {respostaSolicitacao.agendamentoId}</Text>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => navegacao.navigate('AcompanhamentoSaga', { linkAcompanhar: respostaSolicitacao._links.acompanhar })}
                    style={({ pressed }) => [estilos.acaoAcompanhamento, pressed && estilos.acaoAcompanhamentoPressionada]}
                  >
                    <Text style={estilos.textoAcaoAcompanhamento}>Acompanhar solicitação</Text>
                  </Pressable>
                </View>
              )}
              {erroSolicitacao && <Text style={estilos.erroSolicitacao}>{erroSolicitacao}</Text>}
            </>
          ) : (
            <Text style={estilos.textoSecundario}>
              A seleção de horários reais depende da integração com a disponibilidade do Back-End, que ainda não possui uma rota pública para o aplicativo.
            </Text>
          )}
        </Cartao>

        <View style={estilos.secao}>
          <Text style={estilos.tituloSecao}>Selecione um horário</Text>
          <Text style={estilos.textoSecundario}>Disponibilidade demonstrativa, sem consulta a agenda real.</Text>
          <View style={estilos.gradeHorarios}>
            {horariosDemonstracao.map((horario) => {
              const selecionado = horarioSelecionado?.id === horario.id;

              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: selecionado }}
                  key={horario.id}
                  onPress={() => definirHorarioSelecionado(horario)}
                  style={({ pressed }) => [
                    estilos.horario,
                    selecionado && estilos.horarioSelecionado,
                    pressed && !selecionado && estilos.horarioPressionado,
                  ]}
                >
                  <Text style={[estilos.diaHorario, selecionado && estilos.textoHorarioSelecionado]}>
                    {horario.dia}
                  </Text>
                  <Text style={[estilos.valorHorario, selecionado && estilos.textoHorarioSelecionado]}>
                    {horario.horario}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <Cartao estilo={estilos.resumo}>
          <Text style={estilos.tituloSecao}>Resumo da solicitação</Text>
          {horarioSelecionado ? (
            <>
              <Text style={estilos.nomeHemocentro}>Hemocentro Municipal</Text>
              <Text style={estilos.textoSecundario}>
                {horarioSelecionado.dia} às {horarioSelecionado.horario}
              </Text>
            </>
          ) : (
            <Text style={estilos.textoSecundario}>Selecione um horário demonstrativo para continuar.</Text>
          )}
          <BotaoPrimario
            aoPressionar={confirmarDemonstracao}
            desabilitado={!horarioSelecionado}
            titulo="Confirmar solicitação"
          />
          <Pressable
            accessibilityRole="button"
            onPress={() => navegacao.navigate('AcompanhamentoSaga')}
            style={({ pressed }) => [estilos.acaoAcompanhamento, pressed && estilos.acaoAcompanhamentoPressionada]}
          >
            <Text style={estilos.textoAcaoAcompanhamento}>Visualizar acompanhamento demonstrativo</Text>
          </Pressable>
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

function obterMensagemErroSolicitacao(erro: unknown): string {
  if (!(erro instanceof ErroHttp)) {
    return erro instanceof Error ? erro.message : 'Não foi possível enviar a solicitação. Tente novamente.';
  }

  if (erro.categoria === 'CONFLITO') {
    return erro.problema.detail ?? 'Já existe uma solicitação que impede um novo agendamento.';
  }

  if (erro.categoria === 'AUTENTICACAO_NECESSARIA') {
    return 'Sua sessão expirou. Faça login novamente para continuar.';
  }

  if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
    return erro.problema.detail ?? 'O agendamento está temporariamente indisponível. Tente novamente.';
  }

  return erro.problema.detail ?? erro.problema.title;
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartaoCampanha: { gap: espacamentos.medio },
  cartaoDisponibilidadeReal: { gap: espacamentos.medio },
  linhaCartao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesCampanha: { flex: 1, gap: espacamentos.minimo },
  rotulo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  nomeHemocentro: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  avisoDemonstracao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  secao: { gap: espacamentos.pequeno },
  tituloSecao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  gradeHorarios: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.medio, marginTop: espacamentos.pequeno },
  horario: { backgroundColor: cores.cartao, borderRadius: raiosBorda.media, flexBasis: '47%', flexGrow: 1, gap: espacamentos.minimo, minHeight: 88, padding: espacamentos.padrao },
  horarioSelecionado: { backgroundColor: cores.principal },
  horarioPressionado: { backgroundColor: cores.principalClaro },
  diaHorario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  valorHorario: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  textoHorarioSelecionado: { color: cores.cartao },
  resumo: { gap: espacamentos.medio },
  resultadoSolicitacao: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, gap: espacamentos.minimo, padding: espacamentos.medio },
  tituloResultado: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  erroSolicitacao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  acaoAcompanhamento: { alignItems: 'center', minHeight: 48, justifyContent: 'center' },
  acaoAcompanhamentoPressionada: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media },
  textoAcaoAcompanhamento: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
});
