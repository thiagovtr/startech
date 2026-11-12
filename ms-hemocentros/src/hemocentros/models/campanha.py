from datetime import date

from pydantic import BaseModel


class Campanha(BaseModel):
    id: str
    titulo: str
    hemocentro: str
    tipo_sanguineo: str
    status: str
    data_inicio: date
    data_fim: date
