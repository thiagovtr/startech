import { useState } from "react";
import type { PageProps } from "keycloakify/login/pages/PageProps";
import type { KcContext } from "../KcContext";
import type { I18n } from "../i18n";

const FIELD_LABELS_PT: Record<string, string> = {
    firstName: "Nome",
    lastName: "Sobrenome",
    email: "E-mail",
    username: "Usuário"
};

export function Register(props: PageProps<Extract<KcContext, { pageId: "register.ftl" }>, I18n>) {
    const { kcContext, i18n, Template } = props;
    const { url, messagesPerField, passwordRequired, profile } = kcContext;

    const [isSubmitting, setIsSubmitting] = useState(false);

    const attributes = Object.values(profile.attributesByName);

    return (
        <Template
            kcContext={kcContext}
            i18n={i18n}
            doUseDefaultCss={false}
            displayMessage={messagesPerField.exists("global")}
            headerNode="Criar conta de doador"
            infoNode={
                <span>
                    Já possui uma conta?{" "}
                    <a className="st-link" href={url.loginUrl}>
                        Voltar para o login
                    </a>
                </span>
            }
        >
            <form
                className="st-form"
                action={url.registrationAction}
                method="post"
                onSubmit={() => {
                    setIsSubmitting(true);
                    return true;
                }}
            >
                {attributes.map(attribute => {
                    const hasError = messagesPerField.existsError(attribute.name);
                    const label = FIELD_LABELS_PT[attribute.name] ?? attribute.displayName ?? attribute.name;
                    const inputType = attribute.name === "email" ? "email" : "text";

                    return (
                        <div className="st-field" key={attribute.name}>
                            <label className="st-label" htmlFor={attribute.name}>
                                {label}
                            </label>
                            <input
                                id={attribute.name}
                                name={attribute.name}
                                type={inputType}
                                defaultValue={attribute.value ?? ""}
                                required={attribute.required}
                                readOnly={attribute.readOnly}
                                autoComplete={attribute.autocomplete}
                                className={hasError ? "st-input st-input-error" : "st-input"}
                                aria-invalid={hasError}
                            />
                            {hasError && (
                                <span
                                    className="st-field-error"
                                    role="alert"
                                    dangerouslySetInnerHTML={{
                                        __html: messagesPerField.get(attribute.name)
                                    }}
                                />
                            )}
                        </div>
                    );
                })}

                {passwordRequired && (
                    <>
                        <div className="st-field">
                            <label className="st-label" htmlFor="password">
                                Senha
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                required
                                autoComplete="new-password"
                                placeholder="Crie uma senha"
                                className={
                                    messagesPerField.existsError("password")
                                        ? "st-input st-input-error"
                                        : "st-input"
                                }
                            />
                            {messagesPerField.existsError("password") && (
                                <span
                                    className="st-field-error"
                                    role="alert"
                                    dangerouslySetInnerHTML={{
                                        __html: messagesPerField.get("password")
                                    }}
                                />
                            )}
                        </div>

                        <div className="st-field">
                            <label className="st-label" htmlFor="password-confirm">
                                Confirmar senha
                            </label>
                            <input
                                id="password-confirm"
                                name="password-confirm"
                                type="password"
                                required
                                autoComplete="new-password"
                                placeholder="Repita a senha"
                                className={
                                    messagesPerField.existsError("password-confirm")
                                        ? "st-input st-input-error"
                                        : "st-input"
                                }
                            />
                            {messagesPerField.existsError("password-confirm") && (
                                <span
                                    className="st-field-error"
                                    role="alert"
                                    dangerouslySetInnerHTML={{
                                        __html: messagesPerField.get("password-confirm")
                                    }}
                                />
                            )}
                        </div>
                    </>
                )}

                <button className="st-button" type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Cadastrando..." : "Criar conta"}
                </button>
            </form>
        </Template>
    );
}
