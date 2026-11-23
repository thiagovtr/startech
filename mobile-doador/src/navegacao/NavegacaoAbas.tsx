import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';

import { Agendar, Assistente, Inicio, MeusPedidos } from '../telas';
import { cores, espacamentos, pesosFonte, tamanhosFonte } from '../tema';

export type ParametrosAbas = {
  Inicio: undefined;
  Agendar: { slotIdReal?: string } | undefined;
  MeusPedidos: undefined;
  Assistente: undefined;
};

const Abas = createBottomTabNavigator<ParametrosAbas>();

const iconesAbas: Record<keyof ParametrosAbas, string> = {
  Inicio: '⌂',
  Agendar: '+',
  MeusPedidos: '☰',
  Assistente: '?',
};

export function NavegacaoAbas() {
  return (
    <Abas.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: cores.cartao },
        headerTitleStyle: {
          color: cores.texto,
          fontWeight: pesosFonte.seminegrito,
        },
        tabBarActiveTintColor: cores.principal,
        tabBarInactiveTintColor: cores.textoSecundario,
        tabBarLabelStyle: {
          fontSize: tamanhosFonte.legenda,
          fontWeight: pesosFonte.medio,
        },
        tabBarStyle: {
          backgroundColor: cores.cartao,
          borderTopColor: cores.principalClaro,
          paddingTop: espacamentos.minimo,
        },
        tabBarIcon: ({ color }) => (
          <Text accessibilityElementsHidden style={{ color, fontSize: tamanhosFonte.subtitulo }}>
            {iconesAbas[route.name]}
          </Text>
        ),
      })}
    >
      <Abas.Screen component={Inicio} name="Inicio" options={{ title: 'Início' }} />
      <Abas.Screen component={Agendar} name="Agendar" options={{ title: 'Agendar' }} />
      <Abas.Screen component={MeusPedidos} name="MeusPedidos" options={{ title: 'Meus pedidos' }} />
      <Abas.Screen component={Assistente} name="Assistente" options={{ title: 'Assistente' }} />
    </Abas.Navigator>
  );
}
