-- Cancelamento pelo doador (contratos §2 e §3.2): quando e por quê o agendamento foi cancelado.
ALTER TABLE agendamentos
    ADD COLUMN data_cancelamento TIMESTAMP WITH TIME ZONE,
    ADD COLUMN motivo_cancelamento VARCHAR(255);

-- Listagem dos agendamentos do doador (GET /api/v1/agendamentos?doadorId=).
CREATE INDEX idx_agendamentos_doador ON agendamentos(doador_id);
