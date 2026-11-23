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

const conteudoDemonstrativo: Record<SituacaoAcompanhamentoSaga, ConteudoSituacao> = {
  EM_ANDAMENTO: { titulo: 'Solicitação em andamento', descricao: 'Sua solicitação demonstrativa está sendo processada.', selo: 'PENDENTE' },
  CONFIRMADO: { titulo: 'Agendamento confirmado', descricao: 'A solicitação demonstrativa foi concluída com confirmação.', selo: 'CONFIRMADO' },
  RECUSADO: { titulo: 'Solicitação recusada', descricao: 'A solicitação demonstrativa foi recusada.', selo: 'RECUSADO' },
  CANCELADO: { titulo: 'Solicitação compensada', descricao: 'O processamento demonstrativo foi compensado.', selo: 'CANCELADO' },
  ERRO: { titulo: 'Erro de compensação', descricao: 'A compensação demonstrativa não foi concluída.', selo: 'ERRO' },
};

const conteudoReal: Record<SituacaoAcompanhamentoSaga, ConteudoSituacao> = {
  EM_ANDAMENTO: { titulo: 'Solicitação em andamento', descricao: 'Sua solicitação está sendo processada.', selo: 'PENDENTE' },
  CONFIRMADO: { titulo: 'Agendamento confirmado', descricao: 'O BFF informou que a solicitação foi confirmada.', selo: 'CONFIRMADO' },
  RECUSADO: { titulo: 'Solicitação recusada', descricao: 'O BFF informou que a solicitação foi recusada.', selo: 'RECUSADO' },
  CANCELADO: { titulo: 'Solicitação compensada', descricao: 'O BFF informou que o processamento foi compensado.', selo: 'CANCELADO' },
  ERRO: { titulo: 'Erro de compensação', descricao: 'O BFF informou um erro durante a compensação.', selo: 'ERRO' },
};

const opcoesSituacao: { chave: SituacaoAcompanhamentoSaga; titulo: string }[] = [
  { chave: 'EM_ANDAMENTO', titulo: 'Em andamento' },
  { chave: 'CONFIRMADO', titulo: 'Confirmado' },
  { chave: 'RECUSADO', titulo: 'Recusado' },
  { chave: 'CANCELADO', titulo: 'Compensado' },
  { chave: 'ERRO', titulo: 'Erro' },
];

export function AcompanhamentoSaga() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'AcompanhamentoSaga'>>();
  const { clienteHttp } = useContextoAutenticacao();
  const linkAcompanhar = rota.params?.linkAcompanhar;
  const [situacaoDemonstrativa, definirSituacaoDemonstrativa] = useState<SituacaoAcompanhamentoSaga>('EM_ANDAMENTO');
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

  const situacao = respostaAcompanhamento?.situacao ?? situacaoDemonstrativa;
  const conteudo = linkAcompanhar ? conteudoReal[situacao] : conteudoDemonstrativo[situacao];

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Text style={estilos.textoVoltar}>← Voltar para agendar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Acompanhar agendamento</Text>
          <Text style={estilos.descricao}>Consulte a situação da sua solicitação de agendamento.</Text>
        </View>

        {linkAcompanhar && estadoConsulta === 'CARREGANDO' && <EstadoFeedback tipo="carregando" titulo="Consultando solicitação" />}
        {linkAcompanhar && estadoConsulta === 'ERRO' && (
          <EstadoFeedback
            aoTentarNovamente={() => definirTentativaConsulta((tentativa) => tentativa + 1)}
            descricao={mensagemErro}
            tipo="erro"
            titulo="Não foi possível acompanhar a solicitação"
          />
        )}

        {(!linkAcompanhar || (estadoConsulta === 'SUCESSO' && respostaAcompanhamento)) && (
          <Cartao estilo={estilos.cartaoSolicitacao}>
            <View style={estilos.linhaSolicitacao}>
              <View style={estilos.detalhesSolicitacao}>
                <Text style={estilos.rotulo}>{linkAcompanhar ? 'Solicitação' : 'Solicitação demonstrativa'}</Text>
                <Text style={estilos.identificador}>{respostaAcompanhamento?.sagaId ?? 'Demonstração visual'}</Text>
                {respostaAcompanhamento && <Text style={estilos.textoSecundario}>Agendamento: {respostaAcompanhamento.agendamentoId}</Text>}
              </View>
              <SeloStatus situacao={conteudo.selo} />
            </View>
            <View style={estilos.divisor} />
            <Text style={estilos.tituloSituacao}>{conteudo.titulo}</Text>
            <Text style={estilos.descricaoSituacao}>{conteudo.descricao}</Text>
            {respostaAcompanhamento?.motivo && <Motivo texto={respostaAcompanhamento.motivo} />}
            {!linkAcompanhar && motivoDemonstrativo(situacao) && <Motivo texto={motivoDemonstrativo(situacao)!} />}
          </Cartao>
        )}

        {!linkAcompanhar && (
          <View style={estilos.secaoDesenvolvimento}>
            <Text style={estilos.tituloDesenvolvimento}>Ferramenta temporária de desenvolvimento</Text>
            <Text style={estilos.textoSecundario}>Alterne a situação abaixo apenas para testar esta interface.</Text>
            <View style={estilos.opcoesSituacao}>
              {opcoesSituacao.map((opcao) => {
                const estaSelecionada = situacaoDemonstrativa === opcao.chave;
                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: estaSelecionada }}
                    key={opcao.chave}
                    onPress={() => definirSituacaoDemonstrativa(opcao.chave)}
                    style={[estilos.opcaoSituacao, estaSelecionada && estilos.opcaoSituacaoSelecionada]}
                  >
                    <Text style={[estilos.textoOpcaoSituacao, estaSelecionada && estilos.textoOpcaoSituacaoSelecionada]}>{opcao.titulo}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
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

function motivoDemonstrativo(situacao: SituacaoAcompanhamentoSaga): string | undefined {
  if (situacao === 'RECUSADO') return 'Exemplo demonstrativo: não foi possível concluir a solicitação.';
  if (situacao === 'CANCELADO') return 'Exemplo demonstrativo: a solicitação precisou ser desfeita durante o processamento.';
  if (situacao === 'ERRO') return 'Exemplo demonstrativo: ocorreu uma falha técnica durante a compensação.';
  return undefined;
}

function obterMensagemErro(erro: unknown): string {
  if (erro instanceof ErroHttp) return erro.problema.detail ?? erro.problema.title;
  return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignSelf: 'flex-start', justifyContent: 'center', minHeight: 48, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartaoSolicitacao: { gap: espacamentos.medio },
  linhaSolicitacao: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between' },
  detalhesSolicitacao: { flex: 1, gap: espacamentos.minimo },
  rotulo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  identificador: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  divisor: { backgroundColor: cores.principalClaro, height: 1 },
  tituloSituacao: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  descricaoSituacao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  motivo: { backgroundColor: cores.principalClaro, borderRadius: raiosBorda.media, gap: espacamentos.minimo, padding: espacamentos.medio },
  rotuloMotivo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  textoMotivo: { color: cores.texto, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, lineHeight: 20 },
  secaoDesenvolvimento: { gap: espacamentos.medio },
  tituloDesenvolvimento: { color: cores.texto, fontSize: tamanhosFonte.subtitulo, fontWeight: pesosFonte.negrito },
  opcoesSituacao: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.pequeno },
  opcaoSituacao: { backgroundColor: cores.cartao, borderRadius: raiosBorda.arredondada, justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.medio },
  opcaoSituacaoSelecionada: { backgroundColor: cores.principal },
  textoOpcaoSituacao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  textoOpcaoSituacaoSelecionada: { color: cores.cartao },
});
