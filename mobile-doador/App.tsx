import { StatusBar } from 'expo-status-bar';

import { NavegacaoPrincipal } from './src/navegacao';

export default function App() {
  return (
    <>
      <NavegacaoPrincipal />
      <StatusBar style="dark" />
    </>
  );
}
