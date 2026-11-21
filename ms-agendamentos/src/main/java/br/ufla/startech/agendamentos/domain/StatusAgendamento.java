package br.ufla.startech.agendamentos.domain;

public enum StatusAgendamento {
    CRIADO_PROVISORIO,
    CONFIRMADO,
    CANCELADO_DOADOR,
    CANCELADO_COMPENSACAO_SAGA;

    public boolean cancelado() {
        return this == CANCELADO_DOADOR || this == CANCELADO_COMPENSACAO_SAGA;
    }
}
