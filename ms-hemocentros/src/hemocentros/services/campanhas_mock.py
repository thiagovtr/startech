"""Dados fixos (mock) até a implementação do CQRS (Blocos 11-15)."""

from datetime import date

from hemocentros.models.campanha import Campanha

CAMPANHAS_MOCK: list[Campanha] = [
        Campanha(id="camp-001", titulo="Alerta crítico: sangue O-", hemocentro="Hemocentro Regional de Lavras",
                tipo_sanguineo="O-", status="ATIVA", data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 30)),
        Campanha(id="camp-002", titulo="Campanha de fim de ano", hemocentro="Hemocentro Regional de Lavras",
                tipo_sanguineo="A+", status="ATIVA", data_inicio=date(2026, 11, 15), data_fim=date(2026, 12, 20)),
        Campanha(id="camp-003", titulo="Reposição de estoque B-", hemocentro="Hemocentro de Belo Horizonte",
                tipo_sanguineo="B-", status="ATIVA", data_inicio=date(2026, 11, 12), data_fim=date(2026, 12, 5)),
]


def listar(tipo_sanguineo: str | None = None) -> list[Campanha]:
        if tipo_sanguineo is None:
                return CAMPANHAS_MOCK
        return [c for c in CAMPANHAS_MOCK if c.tipo_sanguineo == tipo_sanguineo]
