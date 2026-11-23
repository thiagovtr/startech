import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';
import { BotaoPrimario } from './BotaoPrimario';

export type TipoEstadoFeedback = 'carregando' | 'vazio' | 'erro';

type PropriedadesEstadoFeedback = {
  tipo: TipoEstadoFeedback;
  titulo?: string;
  descricao?: string;
  aoTentarNovamente?: () => void;
};

const conteudoPadrao: Record<TipoEstadoFeedback, { titulo: string; descricao: string }> = {
  carregando: {
    titulo: 'Carregando informações',
    descricao: 'Aguarde um instante.',
  },
  vazio: {
    titulo: 'Nenhuma informação encontrada',
    descricao: 'Não há itens para mostrar no momento.',
  },
  erro: {
    titulo: 'Não foi possível carregar',
    descricao: 'Verifique sua conexão e tente novamente.',
  },
};

export function EstadoFeedback({
  tipo,
  titulo,
  descricao,
  aoTentarNovamente,
}: PropriedadesEstadoFeedback) {
  const conteudo = conteudoPadrao[tipo];

  return (
    <View accessibilityLiveRegion="polite" style={estilos.container}>
      {tipo === 'carregando' && <ActivityIndicator color={cores.principal} size="large" />}
      <Text style={estilos.titulo}>{titulo ?? conteudo.titulo}</Text>
      <Text style={estilos.descricao}>{descricao ?? conteudo.descricao}</Text>
      {tipo === 'erro' && aoTentarNovamente && (
        <View style={estilos.acao}>
          <BotaoPrimario aoPressionar={aoTentarNovamente} titulo="Tentar novamente" />
        </View>
      )}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: {
    alignItems: 'center',
    gap: espacamentos.pequeno,
    paddingHorizontal: espacamentos.muitoGrande,
    paddingVertical: espacamentos.extraGrande,
  },
  titulo: {
    color: cores.texto,
    fontSize: tamanhosFonte.subtitulo,
    fontWeight: pesosFonte.seminegrito,
    textAlign: 'center',
  },
  descricao: {
    color: cores.textoSecundario,
    fontSize: tamanhosFonte.corpo,
    fontWeight: pesosFonte.normal,
    textAlign: 'center',
  },
  acao: {
    alignSelf: 'stretch',
    marginTop: espacamentos.medio,
  },
});
