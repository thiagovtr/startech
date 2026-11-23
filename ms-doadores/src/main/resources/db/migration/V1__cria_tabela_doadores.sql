CREATE TABLE doadores (
    id UUID PRIMARY KEY,
    nome VARCHAR(120) NOT NULL DEFAULT 'Doador StarTech',
    tipo_sanguineo VARCHAR(3) NOT NULL CHECK (tipo_sanguineo IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    criado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO doadores (id, nome, tipo_sanguineo)
VALUES ('11111111-1111-1111-1111-111111111111', 'Doador StarTech', 'O-')
ON CONFLICT (id) DO NOTHING;
