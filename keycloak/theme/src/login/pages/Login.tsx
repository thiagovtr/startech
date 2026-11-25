import { useState } from "react";
import type { PageProps } from "keycloakify/login/pages/PageProps";
import type { KcContext } from "../KcContext";
import type { I18n } from "../i18n";

export function Login(props: PageProps<Extract<KcContext, { pageId: "login.ftl" }>, I18n>) {
    const { kcContext, i18n, Template } = props;
    const { realm, url, usernameHidden, login, messagesPerField, client } = kcContext;

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const isWebClient = client.clientId === "startech-web" || client.clientId === "web";
    const hasCredentialError = messagesPerField.existsError("username", "password");

    return (
        <Template
            kcContext={kcContext}
            i18n={i18n}
            doUseDefaultCss={false}
            displayMessage={!hasCredentialError}
            headerNode={isWebClient ? "Acesso do hemocentro" : "Boas-vindas"}
            infoNode={
                !isWebClient && realm.password && realm.registrationAllowed ? (
                    <span>
                        Ainda não tem cadastro?{" "}
                        <a className="st-link" href={url.registrationUrl}>
                            Criar conta de doador
                        </a>
                    </span>
                ) : null
            }
        >
            <p className="st-description">
                {isWebClient
                    ? "Entre com sua conta de operador para gerenciar campanhas de doação."
                    : "Entre com seu e-mail para acompanhar campanhas, agendar doações e consultar seus pedidos."}
            </p>

            {realm.password && (
                <form
                    className="st-form"
                    action={url.loginAction}
                    method="post"
                    onSubmit={() => {
                        setIsSubmitting(true);
                        return true;
                    }}
                >
                    {!usernameHidden && (
                        <div className="st-field">
                            <label className="st-label" htmlFor="username">
                                {realm.registrationEmailAsUsername
                                    ? "E-mail"
                                    : realm.loginWithEmailAllowed
                                      ? "E-mail ou usuário"
                                      : "Usuário"}
                            </label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                defaultValue={login.username ?? ""}
                                autoFocus
                                autoComplete="username"
                                placeholder={isWebClient ? "operador1@startech.local" : "seuemail@exemplo.com"}
                                className={hasCredentialError ? "st-input st-input-error" : "st-input"}
                                aria-invalid={hasCredentialError}
                            />
                        </div>
                    )}

                    <div className="st-field">
                        <label className="st-label" htmlFor="password">
                            Senha
                        </label>
                        <div className="st-input-wrap">
                            <input
                                id="password"
                                name="password"
                                type={showPassword ? "text" : "password"}
                                autoComplete="current-password"
                                placeholder="Digite sua senha"
                                className={
                                    hasCredentialError
                                        ? "st-input st-input-password st-input-error"
                                        : "st-input st-input-password"
                                }
                                aria-invalid={hasCredentialError}
                            />
                            <button
                                type="button"
                                className="st-toggle-password"
                                onClick={() => setShowPassword(prev => !prev)}
                                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                            >
                                {showPassword ? "Ocultar" : "Mostrar"}
                            </button>
                        </div>

                        {hasCredentialError && (
                            <span
                                className="st-field-error"
                                role="alert"
                                dangerouslySetInnerHTML={{
                                    __html: messagesPerField.getFirstError("username", "password")
                                }}
                            />
                        )}
                    </div>

                    <button className="st-button" type="submit" disabled={isSubmitting}>
                        {isSubmitting ? "Entrando..." : "Entrar"}
                    </button>
                </form>
            )}
        </Template>
    );
}
