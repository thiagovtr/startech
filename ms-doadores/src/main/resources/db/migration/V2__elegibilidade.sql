-- RN01 (Portaria de Consolidação MS nº 5/2017): intervalo mínimo entre doações de sangue total.
ALTER TABLE doadores
    ADD COLUMN sexo VARCHAR(1) NOT NULL DEFAULT 'M' CHECK (sexo IN ('M', 'F')),
    ADD COLUMN data_ultima_doacao DATE;

-- Passo 2 da SAGA: trava temporal do doador enquanto o agendamento está em andamento ou confirmado.
-- O agendamento_id (gerado pelo orquestrador) é a chave de idempotência do passo e da compensação.
CREATE TABLE travas_elegibilidade (
    agendamento_id VARCHAR(64) PRIMARY KEY,
    doador_id UUID NOT NULL REFERENCES doadores (id),
    data_slot TIMESTAMP WITH TIME ZONE NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_travas_elegibilidade_doador ON travas_elegibilidade (doador_id);
