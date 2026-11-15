CREATE TABLE slots (
    id VARCHAR(64) PRIMARY KEY,
    posto_id VARCHAR(64) NOT NULL,
    data_hora_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
    data_hora_fim TIMESTAMP WITH TIME ZONE NOT NULL,
    capacidade INTEGER NOT NULL CHECK (capacidade >= 0),
    vagas_ocupadas INTEGER NOT NULL DEFAULT 0 CHECK (vagas_ocupadas >= 0),
    version BIGINT NOT NULL DEFAULT 0,
    criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_slots_periodo_valido CHECK (data_hora_inicio < data_hora_fim),
    CONSTRAINT chk_slots_vagas_na_capacidade CHECK (vagas_ocupadas <= capacidade)
);

CREATE TABLE agendamentos (
    id VARCHAR(64) PRIMARY KEY,
    doador_id VARCHAR(64) NOT NULL,
    slot_id VARCHAR(64) NOT NULL REFERENCES slots(id),
    status VARCHAR(32) NOT NULL CHECK (status IN (
        'CRIADO_PROVISORIO',
        'CONFIRMADO',
        'CANCELADO_DOADOR',
        'CANCELADO_COMPENSACAO_SAGA'
    )),
    criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_unico_agendamento_ativo
    ON agendamentos(doador_id)
    WHERE status IN ('CRIADO_PROVISORIO', 'CONFIRMADO');
