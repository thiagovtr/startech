import { useState } from 'react';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Cartao, SeloStatus, type SituacaoSelo } from '../componentes';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type SituacaoSaga = 'EM_ANDAMENTO' | 'CONFIRMADO' | 'RECUSADO' | 'CANCELADO' | 'ERRO';

type ConteudoSituacao = {
  titulo: string;
  descricao: string;
  selo: SituacaoSelo;
  motivo?: string;
};

// Valores de situação correspondentes ao contrato do BFF Mobile; conteúdo exibido é demonstrativo.
const conteudoSituacoes: Record<SituacaoSaga, ConteudoSituacao> = {
  EM_ANDAMENTO: {
    titulo: 'Solicitação em andamento',
    descricao: 'Sua solicitação demonstrativa está sendo processada.',
    selo: 'PENDENTE',
  },
  CONFIRMADO: {
    titulo: 'Agendamento confirmado',
    descricao: 'A solicitação demonstrativa foi concluída com confirmação.',
    selo: 'CONFIRMADO',
  },
  RECUSADO: {
    titulo: 'Solicitação recusada',
    descricao: 'A solicitação demonstrativa foi recusada.',
    selo: 'RECUSADO',
    motivo: 'Exemplo demonstrativo: não foi possível concluir a solicitação.',
  },
  CANCELADO: {
    titulo: 'Solicitação compensada',
    descricao: 'O processamento demonstrativo foi compensado.',
    selo: 'CANCELADO',
    motivo: 'Exemplo demonstrativo: a solicitação precisou ser desfeita durante o processamento.',
  },
  ERRO: {
    titulo: 'Erro de compensação',
    descricao: 'A compensação demonstrativa não foi concluída.',
    selo: 'ERRO',
    motivo: 'Exemplo demonstrativo: ocorreu uma falha técnica durante a compensação.',
  },
};

const opcoesSituacao: { chave: SituacaoSaga; titulo: string }[] = [
  { chave: 'EM_ANDAMENTO', titulo: 'Em andamento' },
  { chave: 'CONFIRMADO', titulo: 'Confirmado' },
  { chave: 'RECUSADO', titulo: 'Recusado' },
  { chave: 'CANCELADO', titulo: 'Compensado' },
  { chave: 'ERRO', titulo: 'Erro' },
];

export function AcompanhamentoSaga() {
  const [situacao, definirSituacao] = useState<SituacaoSaga>('EM_ANDAMENTO');
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const conteudo = conteudoSituacoes[situacao];

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

        <Cartao estilo={estilos.cartaoSolicitacao}>
          <View style={estilos.linhaSolicitacao}>
            <View style={estilos.detalhesSolicitacao}>
              <Text style={estilos.rotulo}>Solicitação demonstrativa</Text>
              <Text style={estilos.identificador}>AGD-DEMO-001</Text>
              <Text style={estilos.textoSecundario}>Hemocentro Municipal</Text>
            </View>
            <SeloStatus situacao={conteudo.selo} />
          </View>
          <View style={estilos.divisor} />
          <Text style={estilos.tituloSituacao}>{conteudo.titulo}</Text>
          <Text style={estilos.descricaoSituacao}>{conteudo.descricao}</Text>
          {conteudo.motivo && (
            <View style={estilos.motivo}>
              <Text style={estilos.rotuloMotivo}>Motivo</Text>
              <Text style={estilos.textoMotivo}>{conteudo.motivo}</Text>
            </View>
          )}
        </Cartao>

        <View style={estilos.secaoDesenvolvimento}>
          <Text style={estilos.tituloDesenvolvimento}>Ferramenta temporária de desenvolvimento</Text>
          <Text style={estilos.textoSecundario}>Alterne a situação abaixo apenas para testar esta interface.</Text>
          <View style={estilos.opcoesSituacao}>
            {opcoesSituacao.map((opcao) => {
              const estaSelecionada = situacao === opcao.chave;

              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: estaSelecionada }}
                  key={opcao.chave}
                  onPress={() => definirSituacao(opcao.chave)}
                  style={[estilos.opcaoSituacao, estaSelecionada && estilos.opcaoSituacaoSelecionada]}
                >
                  <Text style={[estilos.textoOpcaoSituacao, estaSelecionada && estilos.textoOpcaoSituacaoSelecionada]}>
                    {opcao.titulo}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
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
  opcaoSituacao: { backgroundColor: cores.cartao, borderRadius: raiosBorda.arredondada, minHeight: 44, paddingHorizontal: espacamentos.medio, justifyContent: 'center' },
  opcaoSituacaoSelecionada: { backgroundColor: cores.principal },
  textoOpcaoSituacao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  textoOpcaoSituacaoSelecionada: { color: cores.cartao },
});
