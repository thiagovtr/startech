import type { TemplateProps } from "keycloakify/login/TemplateProps";
import type { KcContext } from "./KcContext";
import type { I18n } from "./i18n";
import "./styles/startech.css";

/**
 * Moldura visual padrao do tema StarTech, alinhada aos tokens e layout do app mobile-doador.
 */
export function Template(props: TemplateProps<KcContext, I18n>) {
    const {
        displayMessage = true,
        headerNode,
        infoNode = null,
        kcContext,
        children
    } = props;

    const { message, isAppInitiatedAction, client } = kcContext;
    const isWebClient = client.clientId === "startech-web" || client.clientId === "web";

    const alertClass =
        message?.type === "error"
            ? "st-alert st-alert-error"
            : message?.type === "success"
              ? "st-alert st-alert-success"
              : message?.type === "warning"
                ? "st-alert st-alert-warning"
                : "st-alert st-alert-info";

    return (
        <main className="st-page">
            <header className="st-brand">
                <div className="st-brand-badge" aria-label="Identidade StarTech">
                    <span className="st-brand-badge-text">ST</span>
                </div>
                <h1 className="st-brand-name">StarTech</h1>
                <p className="st-brand-subtitle">
                    {isWebClient ? "Painel dos hemocentros" : "Doar sangue é cuidar de vidas."}
                </p>
            </header>

            <section className="st-card" aria-label="Autenticação StarTech">
                {headerNode && <h2 className="st-title">{headerNode}</h2>}

                {displayMessage && message !== undefined && (message.type !== "warning" || !isAppInitiatedAction) && (
                    <div className={alertClass} role="alert">
                        <span dangerouslySetInnerHTML={{ __html: message.summary }} />
                    </div>
                )}

                {children}

                {infoNode && <div className="st-footer-link">{infoNode}</div>}
            </section>

            <footer className="st-meta">
                {isWebClient
                    ? "Acesso restrito a operadores autorizados · OIDC + PKCE"
                    : "Sua próxima doação pode fazer a diferença."}
            </footer>
        </main>
    );
}
