import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useFocusEffect, useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { Cartao, EstadoFeedback, SeloStatus, type SituacaoSelo } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import {
  acompanharSaga,
  ErroHttp,
  type LinkAcompanharAgendamento,
  type RespostaAcompanhamentoSaga,
  type SituacaoAcompanhamentoSaga,
} from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type ConteudoSituacao = {
  titulo: string;
  descricao: string;
  selo: SituacaoSelo;
};

type EstadoConsulta = 'CARREGANDO' | 'SUCESSO' | 'ERRO';

const INTERVALO_CONSULTA_MS = 5000;

const conteudoReal: Record<SituacaoAcompanhamentoSaga, ConteudoSituacao> = {
  EM_ANDAMENTO: { titulo: 'Estamos analisando sua solicitação', descricao: 'Seu agendamento está sendo processado. Você poderá acompanhar o resultado por aqui.', selo: 'PENDENTE' },
  CONFIRMADO: { titulo: 'Agendamento confirmado!', descricao: 'Tudo certo! Seu horário foi reservado com sucesso.', selo: 'CONFIRMADO' },
  RECUSADO: { titulo: 'Não foi possível confirmar seu agendamento', descricao: 'Sua solicitação não pode ser aprovada. Confira o motivo abaixo.', selo: 'RECUSADO' },
  CANCELADO: { titulo: 'Agendamento cancelado', descricao: 'Seu agendamento foi cancelado. Confira os detalhes abaixo.', selo: 'CANCELADO' },
  ERRO: { titulo: 'Não foi possível concluir sua solicitação', descricao: 'Ocorreu um problema durante o processamento. Tente atualizar para consultar a situação.', selo: 'ERRO' },
};

export function AcompanhamentoSaga() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'AcompanhamentoSaga'>>();
  const { clienteHttp } = useContextoAutenticacao();
  const linkAcompanhar = rota.params?.linkAcompanhar;
  const [estadoConsulta, definirEstadoConsulta] = useState<EstadoConsulta>('CARREGANDO');
  const [respostaAcompanhamento, definirRespostaAcompanhamento] = useState<RespostaAcompanhamentoSaga>();
  const [mensagemErro, definirMensagemErro] = useState('');
  const [tentativaConsulta, definirTentativaConsulta] = useState(0);

  useFocusEffect(useCallback(() => {
    const link = linkAcompanhar;
    if (!link) {
      return undefined;
    }
    const linkParaConsulta: LinkAcompanharAgendamento = link;

    let telaAtiva = true;
    let consultaEmAndamento = false;
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    const controlador = new AbortController();

    async function consultar() {
      if (consultaEmAndamento || !telaAtiva) return;
      consultaEmAndamento = true;

      try {
        const resposta = await acompanharSaga(clienteHttp, linkParaConsulta, controlador.signal);
        if (!telaAtiva) return;

        definirRespostaAcompanhamento(resposta);
        definirEstadoConsulta('SUCESSO');
        definirMensagemErro('');

        if (!resposta.finalizada) {
          temporizador = setTimeout(() => void consultar(), INTERVALO_CONSULTA_MS);
        }
      } catch (erro) {
        if (!telaAtiva) return;
        definirEstadoConsulta('ERRO');
        definirMensagemErro(obterMensagemErro(erro));
      } finally {
        consultaEmAndamento = false;
      }
    }

    definirEstadoConsulta('CARREGANDO');
    void consultar();

    return () => {
      telaAtiva = false;
      controlador.abort();
      if (temporizador) clearTimeout(temporizador);
    };
  }, [clienteHttp, linkAcompanhar, tentativaConsulta]));

  const situacao = respostaAcompanhamento?.situacao;
  const conteudo = situacao ? conteudoReal[situacao] : undefined;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para agendamentos" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Acompanhamento da solicitação</Text>
          <Text style={estilos.descricao}>Consulte a situação da sua solicitação de agendamento.</Text>
        </View>

        {!linkAcompanhar && (
          <EstadoFeedback
            descricao="Não foi possível identificar a solicitação para acompanhamento. Volte e tente novamente a partir do agendamento."
            tipo="erro"
            titulo="Link de acompanhamento indisponível"
          />
        )}
        {linkAcompanhar && estadoConsulta === 'CARREGANDO' && (
          <EstadoFeedback
            descricao="Estamos verificando a disponibilidade e as condições para confirmar seu agendamento."
            tipo="carregando"
            titulo="Solicitação recebida!"
          />
        )}
        {linkAcompanhar && estadoConsulta === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => definirTentativaConsulta((tentativa) => tentativa + 1)}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível acompanhar a solicitação"
          />
        )}

        {linkAcompanhar && estadoConsulta === 'SUCESSO' && respostaAcompanhamento && conteudo && (
          <Cartao estilo={estilos.cartaoSolicitacao}>
            <View style={estilos.linhaSolicitacao}>
              <View style={estilos.detalhesSolicitacao}>
                <Text style={estilos.rotulo}>Solicitação</Text>
                <Text style={estilos.identificador}>{respostaAcompanhamento.sagaId}</Text>
                <Text style={estilos.textoSecundario}>Agendamento: {respostaAcompanhamento.agendamentoId}</Text>
              </View>
              <SeloStatus situacao={conteudo.selo} />
            </View>
            <View style={estilos.divisor} />
            <Text style={estilos.tituloSituacao}>{conteudo.titulo}</Text>
            <Text style={estilos.descricaoSituacao}>{conteudo.descricao}</Text>
            {respostaAcompanhamento.motivo && <Motivo texto={respostaAcompanhamento.motivo} />}
            {respostaAcompanhamento._links.agendamento && (
              <Pressable
                accessibilityRole="button"
                onPress={() => navegacao.navigate('DetalhesAgendamento', { linkConsultar: respostaAcompanhamento._links.agendamento! })}
                style={({ pressed }) => [estilos.acaoDetalhes, pressed && estilos.acaoDetalhesPressionada]}
              >
                <Text style={estilos.textoAcaoDetalhes}>Ver detalhes do agendamento</Text>
              </Pressable>
            )}
          </Cartao>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

function Motivo({ texto }: { texto: string }) {
  return (
    <View style={estilos.motivo}>
      <Text style={estilos.rotuloMotivo}>Motivo</Text>
      <Text style={estilos.textoMotivo}>{texto}</Text>
    </View>
  );
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) return erro.problema.detail ?? erro.problema.title;
  return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartaoSolicitacao: { gap: espacamentos.medio, padding: espacamentos.medio },
  linhaSolicitacao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesSolicitacao: { flex: 1, gap: espacamentos.minimo },
  rotulo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  identificador: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  divisor: { backgroundColor: cores.principalClaro, height: 1 },
  tituloSituacao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  descricaoSituacao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  motivo: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, gap: espacamentos.minimo, padding: espacamentos.pequeno },
  rotuloMotivo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  textoMotivo: { color: cores.texto, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, lineHeight: 20 },
  acaoDetalhes: { alignItems: 'center', minHeight: 48, justifyContent: 'center' },
  acaoDetalhesPressionada: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media },
  textoAcaoDetalhes: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
});
