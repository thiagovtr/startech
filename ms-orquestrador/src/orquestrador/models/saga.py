"""DTOs da API da SAGA (JSON em camelCase, conforme a especificação de contratos)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from orquestrador.models.orm import SagaExecucao, SagaPassoLog
from orquestrador.saga.estados import STATUS_TERMINAIS, StatusSaga

Identificador = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SagaAgendamentoCriar(_Camel):
    doador_id: Identificador = Field(examples=["5f0c8a6e-2b1d-4c35-9a77-0e4c2f1b9d10"])
    slot_id: Identificador = Field(examples=["slot-20261125-1400"])


class Link(BaseModel):
    href: str
    method: str = "GET"


class SagaCriada(_Camel):
    saga_id: uuid.UUID
    agendamento_id: str
    status: StatusSaga
    links: dict[str, Link] = Field(serialization_alias="_links")


class PassoExecutado(_Camel):
    passo: str
    direcao: str
    resultado: str
    detalhe: dict[str, Any] | None
    em: datetime


class SagaDetalhe(_Camel):
    saga_id: uuid.UUID
    agendamento_id: str
    doador_id: str
    slot_id: str
    status: StatusSaga
    finalizada: bool
    passo_atual: str
    tentativas: int
    data_hora_inicio: str | None = Field(description="Início do slot, devolvido pelo passo 1")
    recusa: dict[str, Any] | None = Field(description="problem+json da recusa de negócio, quando houver")
    erro: str | None = Field(description="Última falha técnica registrada")
    criada_em: datetime
    atualizada_em: datetime
    passos: list[PassoExecutado]


def link_da_saga(saga_id: uuid.UUID) -> str:
    return f"/api/v1/sagas/{saga_id}"


def criada(saga: SagaExecucao) -> SagaCriada:
    return SagaCriada(
        saga_id=saga.saga_id, agendamento_id=saga.agendamento_id, status=StatusSaga(saga.status),
        links={"self": Link(href=link_da_saga(saga.saga_id))},
    )


def detalhe(saga: SagaExecucao, log: list[SagaPassoLog]) -> SagaDetalhe:
    status = StatusSaga(saga.status)
    return SagaDetalhe(
        saga_id=saga.saga_id, agendamento_id=saga.agendamento_id, doador_id=saga.doador_id, slot_id=saga.slot_id,
        status=status, finalizada=status in STATUS_TERMINAIS, passo_atual=saga.current_step,
        tentativas=saga.retry_count, data_hora_inicio=(saga.payload or {}).get("dataHoraInicio"),
        recusa=saga.recusa, erro=saga.error_detail, criada_em=saga.created_at, atualizada_em=saga.updated_at,
        passos=[
            PassoExecutado(passo=r.step, direcao=r.acao, resultado=r.resultado, detalhe=r.detalhe, em=r.criado_em)
            for r in log
        ],
    )
