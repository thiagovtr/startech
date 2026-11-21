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

import { BotaoPrimario, Cartao } from '../componentes';
import { cores, espacamentos, pesosFonte, raiosBorda, tamanhosFonte } from '../tema';

type FonteAssistente = {
  secao: string;
  fonte: string;
  trecho: string;
};

type MensagemAssistente = {
  id: string;
  autor: 'USUARIO' | 'ASSISTENTE';
  texto: string;
  modo?: string;
  fontes?: FonteAssistente[];
  degradado?: boolean;
};

const mensagemInicial: MensagemAssistente = {
  id: 'boas-vindas',
  autor: 'ASSISTENTE',
  texto: 'Olá! Sou o Assistente StarTech. Envie uma pergunta para visualizar esta demonstração.',
  modo: 'DEMONSTRACAO',
};

export function Assistente() {
  const [pergunta, definirPergunta] = useState('');
  const [mensagens, definirMensagens] = useState<MensagemAssistente[]>([mensagemInicial]);
  const [carregando, definirCarregando] = useState(false);
  const [erroCampo, definirErroCampo] = useState('');

  function enviarPergunta() {
    const perguntaNormalizada = pergunta.trim();

    if (!perguntaNormalizada) {
      definirErroCampo('Digite uma pergunta para continuar.');
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

    // Resposta temporária até a integração com POST /api/mobile/assistente.
    setTimeout(() => {
      definirMensagens((mensagensAtuais) => [
        ...mensagensAtuais,
        {
          id: `assistente-${Date.now()}`,
          autor: 'ASSISTENTE',
          texto: 'Esta é uma resposta demonstrativa. O assistente real será integrado em uma próxima etapa.',
          modo: 'DEMONSTRACAO',
          fontes: [
            {
              secao: 'Demonstração',
              fonte: 'Fonte temporária',
              trecho: 'As fontes reais serão apresentadas após a integração.',
            },
          ],
          degradado: false,
        },
      ]);
      definirCarregando(false);
    }, 500);
  }

  function simularFallback() {
    definirMensagens((mensagensAtuais) => [
      ...mensagensAtuais,
      {
        id: `fallback-${Date.now()}`,
        autor: 'ASSISTENTE',
        texto: 'O assistente está temporariamente indisponível. Tente novamente em instantes.',
        modo: 'FALLBACK',
        fontes: [],
        degradado: true,
      },
    ]);
  }

  return (
    <SafeAreaView edges={['right', 'left']} style={estilos.areaSegura}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.areaTeclado}>
        <View style={estilos.cabecalho}>
          <View>
            <Text style={estilos.titulo}>Assistente StarTech</Text>
            <Text style={estilos.descricao}>Tire dúvidas e acompanhe informações pelo aplicativo.</Text>
          </View>
          <Pressable accessibilityRole="button" onPress={simularFallback} style={estilos.acaoFallback}>
            <Text style={estilos.textoAcaoFallback}>Simular fallback</Text>
          </Pressable>
        </View>

        <Text style={estilos.avisoDemonstracao}>Respostas demonstrativas — sem conexão com o assistente real.</Text>

        <ScrollView contentContainerStyle={estilos.listaMensagens} keyboardShouldPersistTaps="handled">
          {mensagens.map((mensagem) => {
            const eUsuario = mensagem.autor === 'USUARIO';
            const eFallback = mensagem.modo === 'FALLBACK' || mensagem.degradado === true;

            return (
              <View key={mensagem.id} style={[estilos.linhaMensagem, eUsuario && estilos.linhaMensagemUsuario]}>
                {eUsuario ? (
                  <View style={estilos.mensagemUsuario}>
                    <Text style={estilos.textoUsuario}>{mensagem.texto}</Text>
                  </View>
                ) : (
                  <Cartao estilo={estilos.mensagemAssistente}>
                    {eFallback && <Text style={estilos.avisoFallback}>Assistente temporariamente indisponível</Text>}
                    <Text style={estilos.textoAssistente}>{mensagem.texto}</Text>
                    {mensagem.fontes && mensagem.fontes.length > 0 && (
                      <View style={estilos.fontes}>
                        <Text style={estilos.tituloFontes}>Fontes</Text>
                        {mensagem.fontes.map((fonte) => (
                          <View key={`${fonte.secao}-${fonte.fonte}`} style={estilos.fonte}>
                            <Text style={estilos.nomeFonte}>{fonte.fonte}</Text>
                            <Text style={estilos.trechoFonte}>{fonte.trecho}</Text>
                          </View>
                        ))}
                      </View>
                    )}
                  </Cartao>
                )}
              </View>
            );
          })}
          {carregando && (
            <Cartao estilo={estilos.mensagemAssistente}>
              <View style={estilos.carregamento}>
                <ActivityIndicator color={cores.principal} />
                <Text style={estilos.textoSecundario}>Preparando resposta demonstrativa...</Text>
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
          <BotaoPrimario aoPressionar={enviarPergunta} carregando={carregando} titulo="Enviar" />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  areaTeclado: { flex: 1 },
  cabecalho: { alignItems: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, justifyContent: 'space-between', padding: espacamentos.padrao },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal, marginTop: espacamentos.minimo },
  acaoFallback: { alignItems: 'center', justifyContent: 'center', minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoAcaoFallback: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  avisoDemonstracao: { backgroundColor: cores.principalClaro, color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio, marginHorizontal: espacamentos.padrao, padding: espacamentos.pequeno, textAlign: 'center' },
  listaMensagens: { gap: espacamentos.medio, padding: espacamentos.padrao, paddingBottom: espacamentos.muitoGrande },
  linhaMensagem: { alignSelf: 'flex-start', maxWidth: '88%' },
  linhaMensagemUsuario: { alignSelf: 'flex-end' },
  mensagemUsuario: { backgroundColor: cores.principal, borderRadius: raiosBorda.grande, padding: espacamentos.padrao },
  mensagemAssistente: { gap: espacamentos.pequeno },
  textoUsuario: { color: cores.cartao, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 22 },
  textoAssistente: { color: cores.texto, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 22 },
  avisoFallback: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.negrito },
  fontes: { borderTopColor: cores.principalClaro, borderTopWidth: 1, gap: espacamentos.pequeno, marginTop: espacamentos.pequeno, paddingTop: espacamentos.pequeno },
  tituloFontes: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.seminegrito },
  fonte: { gap: espacamentos.minimo },
  nomeFonte: { color: cores.texto, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
  trechoFonte: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  carregamento: { alignItems: 'center', flexDirection: 'row', gap: espacamentos.pequeno },
  textoSecundario: { color: cores.textoSecundario, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.normal },
  compositor: { backgroundColor: cores.cartao, borderTopColor: cores.principalClaro, borderTopWidth: 1, gap: espacamentos.pequeno, padding: espacamentos.padrao },
  campoPergunta: { backgroundColor: cores.fundo, borderColor: cores.principalClaro, borderRadius: raiosBorda.media, borderWidth: 1, color: cores.texto, fontSize: tamanhosFonte.corpo, maxHeight: 120, minHeight: 52, paddingHorizontal: espacamentos.medio, paddingVertical: espacamentos.pequeno, textAlignVertical: 'top' },
  erroCampo: { color: cores.principalEscuro, fontSize: tamanhosFonte.legenda, fontWeight: pesosFonte.medio },
});
