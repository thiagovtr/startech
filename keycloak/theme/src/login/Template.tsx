import type { TemplateProps } from "keycloakify/login/TemplateProps";
import type { KcContext } from "./KcContext";
import type { I18n } from "./i18n";
import "./styles/startech.css";

/**
 * Moldura visual padrao do tema StarTech, alinhada aos tokens de design do app mobile.
 */
export function Template(props: TemplateProps<KcContext, I18n>) {
    const {
        displayMessage = true,
        headerNode,
        infoNode = null,
        kcContext,
        children
    } = props;

    const { message, isAppInitiatedAction } = kcContext;

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
            <section className="st-card" aria-label="Autenticação StarTech">
                <header className="st-brand">
                    <div className="st-brand-badge" aria-hidden="true">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2.25C12 2.25 5.25 10.08 5.25 14.625C5.25 18.352 8.273 21.375 12 21.375C15.727 21.375 18.75 18.352 18.75 14.625C18.75 10.08 12 2.25 12 2.25Z" />
                        </svg>
                    </div>
                    <h1 className="st-brand-name">StarTech</h1>
                    <p className="st-brand-subtitle">Plataforma de Doação de Sangue</p>
                </header>

                {headerNode && <h2 className="st-title">{headerNode}</h2>}

                {displayMessage && message !== undefined && (message.type !== "warning" || !isAppInitiatedAction) && (
                    <div className={alertClass} role="alert">
                        <span dangerouslySetInnerHTML={{ __html: message.summary }} />
                    </div>
                )}

                {children}

                {infoNode && <div className="st-footer-link">{infoNode}</div>}
            </section>

            <footer className="st-meta">Acesso seguro via Keycloak (OIDC + PKCE)</footer>
        </main>
    );
}
