import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import { KcPage } from "./login/KcPage";
import type { KcContext } from "./login/KcContext";

declare global {
    interface Window {
        kcContext?: KcContext;
    }
}

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        {window.kcContext ? (
            <KcPage kcContext={window.kcContext} />
        ) : (
            <div style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", textAlign: "center" }}>
                <h1>StarTech — Tema Keycloak</h1>
                <p>Este tema deve ser renderizado pelo servidor Keycloak (realm startech).</p>
            </div>
        )}
    </StrictMode>
);
