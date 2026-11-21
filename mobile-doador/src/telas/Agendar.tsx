import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BotaoPrimario, Cartao, SeloStatus } from '../componentes';
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

  function confirmarDemonstracao() {
    Alert.alert(
      'Funcionalidade em demonstração',
      'A solicitação não foi enviada. O agendamento real será integrado em uma próxima etapa.',
    );
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
        </Cartao>
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  cartaoCampanha: { gap: espacamentos.medio },
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
});
