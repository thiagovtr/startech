import { useState } from "react";
import type { PageProps } from "keycloakify/login/pages/PageProps";
import type { KcContext } from "../KcContext";
import type { I18n } from "../i18n";

export function Login(props: PageProps<Extract<KcContext, { pageId: "login.ftl" }>, I18n>) {
    const { kcContext, i18n, Template } = props;
    const { realm, url, usernameHidden, login, messagesPerField } = kcContext;

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const hasCredentialError = messagesPerField.existsError("username", "password");

    return (
        <Template
            kcContext={kcContext}
            i18n={i18n}
            doUseDefaultCss={false}
            displayMessage={!hasCredentialError}
            headerNode="Entrar na sua conta"
            infoNode={
                realm.password && realm.registrationAllowed ? (
                    <span>
                        Ainda não tem cadastro?{" "}
                        <a className="st-link" href={url.registrationUrl}>
                            Criar conta de doador
                        </a>
                    </span>
                ) : null
            }
        >
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
                                {realm.loginWithEmailAllowed ? "Usuário ou e-mail" : "Usuário"}
                            </label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                defaultValue={login.username ?? ""}
                                autoFocus
                                autoComplete="username"
                                placeholder="Ex.: doador1 ou operador1"
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
