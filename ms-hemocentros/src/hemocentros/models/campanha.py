from datetime import date

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Campanha(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    hemocentro: str
    tipo_sanguineo: str
    urgencia: str = "NORMAL"
    status: str
    data_inicio: date
    data_fim: date


class CampanhaCriar(BaseModel):
    """Payload do POST /api/v1/campanhas."""

    titulo: str = Field(min_length=3, max_length=200)
    hemocentro: str = Field(min_length=2, max_length=200)
    tipo_sanguineo: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    urgencia: Literal["NORMAL", "CRITICO"] = "NORMAL"
    data_inicio: date
    data_fim: date

    @model_validator(mode="after")
    def _periodo_valido(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")
        return self
