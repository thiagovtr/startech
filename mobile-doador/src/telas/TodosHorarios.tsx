import { Ionicons } from '@expo/vector-icons';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CartaoHorario } from './Agendar';
import type { ParametrosRaiz } from '../navegacao/NavegacaoPrincipal';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export function TodosHorarios() {
  const navegacao = useNavigation<NativeStackNavigationProp<ParametrosRaiz>>();
  const rota = useRoute<RouteProp<ParametrosRaiz, 'TodosHorarios'>>();
  const { slots } = rota.params;

  return (
    <SafeAreaView edges={['top', 'right', 'bottom', 'left']} style={estilos.areaSegura}>
      <ScrollView contentContainerStyle={estilos.conteudo}>
        <Pressable accessibilityLabel="Voltar para Agendamentos" accessibilityRole="button" onPress={() => navegacao.goBack()} style={estilos.voltar}>
          <Ionicons color={cores.principalEscuro} name="arrow-back" size={20} />
          <Text style={estilos.textoVoltar}>Voltar</Text>
        </Pressable>

        <View style={estilos.cabecalho}>
          <Text style={estilos.titulo}>Todos os horários</Text>
          <Text style={estilos.descricao}>Escolha um horário disponível para conferir antes de enviar sua solicitação.</Text>
        </View>

        <View style={estilos.listaSlots}>
          {slots.map((slot) => (
            <CartaoHorario
              aoSelecionar={() => navegacao.navigate('ResumoAgendamento', { slot })}
              key={slot.slotId}
              slot={slot}
            />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  areaSegura: { backgroundColor: cores.fundo, flex: 1 },
  conteudo: { gap: espacamentos.muitoGrande, padding: espacamentos.padrao, paddingBottom: espacamentos.extraGrande },
  voltar: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: espacamentos.pequeno, minHeight: 44, paddingHorizontal: espacamentos.pequeno },
  textoVoltar: { color: cores.principalEscuro, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.seminegrito },
  cabecalho: { gap: espacamentos.pequeno },
  titulo: { color: cores.texto, fontSize: tamanhosFonte.titulo, fontWeight: pesosFonte.negrito },
  descricao: { color: cores.textoSecundario, fontSize: tamanhosFonte.corpo, fontWeight: pesosFonte.normal, lineHeight: 24 },
  listaSlots: { gap: espacamentos.medio },
});
