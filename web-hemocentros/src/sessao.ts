import Keycloak from "keycloak-js";
import { clienteCampanhas, ErroCampanhas } from "./campanhas";

export const sessao = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8089",
  realm: "startech",
  clientId: "startech-web"
});

export const retorno = window.location.origin + "/";
export const campanhas = clienteCampanhas(import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080", async () => {
  try {
    await sessao.updateToken(30);
  } catch {
    if (sessao.authenticated) throw new Error("Não foi possível renovar a sessão no Keycloak. Tente novamente.");
  }
  if (!sessao.authenticated || !sessao.token) throw new ErroCampanhas(401, "Sua sessão expirou. Entre novamente.");
  return sessao.token;
});
