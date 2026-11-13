"""Modelos de contrato do BFF Web (campanhas).

O BFF repassa o comando ao `ms-hemocentros`, que é a **única fonte das regras de negócio** (valores
permitidos de `tipo_sanguineo`/`urgencia`, tamanhos, `data_fim >= data_inicio`). Aqui os campos são tipados
só para documentar o OpenAPI e barrar payload estruturalmente inválido (campo ausente ou de tipo errado);
as regras de domínio não são duplicadas, para não divergirem do serviço.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CampanhaCriar(BaseModel):
    model_config = ConfigDict(
        extra="allow",  # campos novos do serviço passam sem exigir mudança no BFF
        json_schema_extra={
            "example": {
                "titulo": "Alerta O- - Lavras",
                "hemocentro": "Hemocentro de Lavras",
                "tipo_sanguineo": "O-",
                "urgencia": "CRITICO",
                "data_inicio": "2026-11-10",
                "data_fim": "2026-11-30",
            }
        },
    )

    titulo: str = Field(description="3 a 200 caracteres (validado pelo ms-hemocentros).")
    hemocentro: str = Field(description="Nome do hemocentro; 2 a 200 caracteres.")
    tipo_sanguineo: str = Field(description="Um de: A+, A-, B+, B-, AB+, AB-, O+, O-.", examples=["O-"])
    urgencia: str = Field(default="NORMAL", description="NORMAL (padrão) ou CRITICO.")
    data_inicio: date = Field(description="Formato AAAA-MM-DD.")
    data_fim: date = Field(description="Formato AAAA-MM-DD; não pode ser anterior a data_inicio.")


class Campanha(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    titulo: str
    hemocentro: str
    tipo_sanguineo: str
    urgencia: str
    status: str = Field(description="Hoje, sempre ATIVA na criação.")
    data_inicio: str
    data_fim: str
