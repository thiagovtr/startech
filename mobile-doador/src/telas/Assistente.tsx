import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useContextoAutenticacao } from '../autenticacao';
import { BotaoPrimario, Cartao } from '../componentes';
import { ErroHttp, perguntarAssistente, type FonteAssistente, type ModoAssistente } from '../servicos';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type MensagemAssistente = {
  id: string;
  autor: 'USUARIO' | 'ASSISTENTE';
  texto: string;
  modo?: ModoAssistente | null;
  fontes?: FonteAssistente[];
  degradado?: boolean;
  motivo?: string;
  erro?: boolean;
};

const mensagemInicial: MensagemAssistente = {
  id: 'boas-vindas',
  autor: 'ASSISTENTE',
  texto: 'Olá! Sou o Assistente StarTech. Envie uma pergunta para receber uma resposta do serviço de apoio ao doador.',
};

const sugestoesIniciais = [
  'O que é preciso para doar sangue?',
  'Fiz tatuagem há 3 meses, posso doar?',
  'Qual o intervalo entre doações?',
  'Onde posso doar sangue hoje?',
];

export function Assistente() {
  const { clienteHttp } = useContextoAutenticacao();
  const [pergunta, definirPergunta] = useState('');
  const [mensagens, definirMensagens] = useState<MensagemAssistente[]>([mensagemInicial]);
  const [carregando, definirCarregando] = useState(false);
  const [erroCampo, definirErroCampo] = useState('');

  async function enviarPergunta(textoDireto?: string) {
    const perguntaNormalizada = (textoDireto ?? pergunta).trim();

    if (!perguntaNormalizada) {
      definirErroCampo('Digite uma pergunta para continuar.');
      return;
    }

    if (perguntaNormalizada.length < 3) {
      definirErroCampo('Digite uma pergunta com pelo menos 3 caracteres.');
      return;
    }

    const mensagemUsuario: MensagemAssistente = {
      id: `usuario-${Date.now()}`,
      autor: 'USUARIO',
      texto: perguntaNormalizada,
    };

    definirMensagens((mensagensAtuais) => [...mensagensAtuais, mensagemUsuario]);
    definirPergunta('');
    definirErroCampo('');
    definirCarregando(true);

    try {
      const resposta = await perguntarAssistente(clienteHttp, { pergunta: perguntaNormalizada });
      definirMensagens((mensagensAtuais) => [
        ...mensagensAtuais,
        {
          id: `assistente-${Date.now()}`,
          autor: 'ASSISTENTE',
          degradado: resposta.degradado,
          fontes: resposta.fontes,
          modo: resposta.modo,
          motivo: resposta.motivo,
          texto: resposta.resposta ?? 'O assistente não retornou uma resposta em texto.',
        },
      ]);
    } catch (erro) {
      definirMensagens((mensagensAtuais) => [
        ...mensagensAtuais,
        {
          id: `erro-${Date.now()}`,
          autor: 'ASSISTENTE',
          erro: true,
          texto: obterMensagemErro(erro),
        },
      ]);
    } finally {
      definirCarregando(false);
    }
  }

  return (
    <SafeAreaView edges={['top', 'right', 'left']} style={estilos.areaSegura}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.areaTeclado}>
        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Assistente</Text>
          <Text style={estilos.descricao}>Tire dúvidas sobre doação de sangue e o StarTech.</Text>
        </View>

        <ScrollView contentContainerStyle={estilos.listaMensagens} keyboardShouldPersistTaps="handled">
          {mensagens.map((mensagem) => <Mensagem key={mensagem.id} mensagem={mensagem} />)}
          {mensagens.length === 1 && !carregando && (
            <View style={estilos.sugestoes}>
              <Text style={estilos.tituloSugestoes}>Perguntas comuns</Text>
              <View style={estilos.listaSugestoes}>
                {sugestoesIniciais.map((sugestao) => (
                  <Pressable
                    accessibilityRole="button"
                    key={sugestao}
                    onPress={() => void enviarPergunta(sugestao)}
                    style={({ pressed }) => [estilos.chipSugestao, pressed && estilos.chipSugestaoPressionado]}
                  >
                    <Text style={estilos.textoSugestao}>{sugestao}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          )}
          {carregando && (
            <Cartao estilo={estilos.mensagemAssistente}>
              <View style={estilos.carregamento}>
                <ActivityIndicator color={cores.principal} />
                <Text style={estilos.textoSecundario}>Consultando o assistente...</Text>
              </View>
            </Cartao>
          )}
        </ScrollView>

        <View style={estilos.compositor}>
          <TextInput
            accessibilityLabel="Digite sua pergunta"
            editable={!carregando}
            maxLength={500}
            multiline
            onChangeText={(texto) => {
              definirPergunta(texto);
              definirErroCampo('');
            }}
            placeholder="Digite sua pergunta"
            placeholderTextColor={cores.textoSecundario}
            style={estilos.campoPergunta}
            value={pergunta}
          />
          {erroCampo && <Text style={estilos.erroCampo}>{erroCampo}</Text>}
          <BotaoPrimario aoPressionar={() => void enviarPergunta()} carregando={carregando} titulo="Enviar" />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Mensagem({ mensagem }: { mensagem: MensagemAssistente }) {
  const eUsuario = mensagem.autor === 'USUARIO';
  const eFallback = mensagem.modo === 'FALLBACK' || mensagem.degradado === true;

  return (
    <View style={[estilos.linhaMensagem, eUsuario && estilos.linhaMensagemUsuario]}>
      {eUsuario ? (
        <View style={estilos.mensagemUsuario}><Text style={estilos.textoUsuario}>{mensagem.texto}</Text></View>
      ) : (
        <Cartao estilo={[estilos.mensagemAssistente, mensagem.erro && estilos.mensagemErro]}>
          {eFallback && <Text style={estilos.avisoFallback}>Assistente temporariamente indisponível</Text>}
          {mensagem.erro && <Text style={estilos.avisoFallback}>Não foi possível consultar o assistente</Text>}
          <Text style={estilos.textoAssistente}>{mensagem.texto}</Text>
          {mensagem.modo && <Text style={estilos.modo}>Modo: {mensagem.modo}</Text>}
          {mensagem.motivo && <Text style={estilos.motivo}>Detalhe: {mensagem.motivo}</Text>}
          {mensagem.fontes && mensagem.fontes.length > 0 && <Fontes fontes={mensagem.fontes} />}
        </Cartao>
      )}
    </View>
  );
}

function Fontes({ fontes }: { fontes: FonteAssistente[] }) {
  return (
    <View style={estilos.fontes}>
      <Text style={estilos.tituloFontes}>Fontes</Text>
      {fontes.map((fonte, indice) => (
        <View key={`${fonte.secao}-${fonte.fonte}-${indice}`} style={estilos.fonte}>
          <Text style={estilos.nomeFonte}>{fonte.fonte}</Text>
          <Text style={estilos.secaoFonte}>{fonte.secao}</Text>
          <Text style={estilos.trechoFonte}>{fonte.trecho}</Text>
        </View>
      ))}
    </View>
  );
}

function obterMensagemErro(erro: unknown): string {
  if (!(erro instanceof ErroHttp)) return erro instanceof Error ? erro.message : 'Tente novamente em alguns instantes.';
  if (erro.categoria === 'AUTENTICACAO_NECESSARIA') return 'Sua sessão expirou. Faça login novamente para continuar.';
  if (erro.categoria === 'SERVICO_INDISPONIVEL' || erro.categoria === 'REDE') {
    return erro.problema.detail ?? 'O assistente está temporariamente indisponível. Tente novamente em instantes.';
  }
  return erro.problema.detail ?? erro.problema.title;
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  areaTeclado: { flex: 1 },
  cabecalho: { gap: espacamentos.minimo, padding: espacamentos.padrao },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  listaMensagens: { gap: espacamentos.medio, padding: espacamentos.padrao, paddingBottom: espacamentos.muitoGrande },
  linhaMensagem: { alignSelf: 'flex-start', maxWidth: '88%' },
  linhaMensagemUsuario: { alignSelf: 'flex-end' },
  mensagemUsuario: { backgroundColor: cores.principal, borderRadius: raiosBorda.grande, padding: espacamentos.padrao },
  mensagemAssistente: { gap: espacamentos.pequeno },
  mensagemErro: { backgroundColor: cores.principalClaro },
  textoUsuario: { color: cores.cartao, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 22 },
  textoAssistente: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 22 },
  avisoFallback: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.negrito },
  modo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  motivo: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  fontes: { borderTopColor: cores.principalClaro, borderTopWidth: 1, gap: espacamentos.pequeno, marginTop: espacamentos.pequeno, paddingTop: espacamentos.pequeno },
  tituloFontes: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  fonte: { gap: espacamentos.minimo },
  nomeFonte: { color: cores.texto, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  secaoFonte: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  trechoFonte: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  carregamento: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.pequeno },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  compositor: { backgroundColor: cores.cartao, borderTopColor: cores.principalClaro, borderTopWidth: 1, gap: espacamentos.pequeno, marginBottom: espacamentos.gigante * 3, padding: espacamentos.padrao },
  campoPergunta: { backgroundColor: cores.fundo, borderColor: cores.principalClaro, borderRadius: raiosBorda.media, borderWidth: 1, color: cores.texto, fontSize: tamanhosFonte.corpo, maxHeight: 120, minHeight: 52, paddingHorizontal: espacamentos.medio, paddingVertical: espacamentos.pequeno, textAlignVertical: 'top' },
  erroCampo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  sugestoes: { gap: espacamentos.pequeno, marginTop: espacamentos.pequeno },
  tituloSugestoes: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  listaSugestoes: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamentos.pequeno },
  chipSugestao: { backgroundColor: cores.cartao, borderColor: cores.principalClaro, borderRadius: raiosBorda.media, borderWidth: 1, paddingHorizontal: espacamentos.medio, paddingVertical: espacamentos.pequeno },
  chipSugestaoPressionado: { backgroundColor: cores.principalClaro },
  textoSugestao: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
});
