"""API da SAGA de agendamento (contratos §2, linhas "5. orquestrador")."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from orquestrador.api.errors import problem
from orquestrador.models import saga as dto
from orquestrador.observabilidade import request_id_var
from orquestrador.repositories import sagas as repo
from orquestrador.services.workers import disparar

router = APIRouter(prefix="/api/v1/sagas", tags=["sagas"])


@router.post(
    "/agendamento",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dto.SagaCriada,
    response_model_by_alias=True,
    responses={
        409: {"description": "Doador já possui SAGA de agendamento em andamento (RN09)"},
        422: {"description": "Idempotency-Key já usada com outro doador ou slot"},
    },
)
async def iniciar_agendamento(
    request: Request,
    corpo: dto.SagaAgendamentoCriar,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
):
    """Inicia a SAGA (202 + `Location`); o andamento é acompanhado por `GET /api/v1/sagas/{sagaId}`.

    A mesma `Idempotency-Key` devolve a SAGA já criada, sem iniciar outra.
    """
    state = request.app.state
    try:
        criacao = await repo.criar(
            state.session_factory, doador_id=corpo.doador_id, slot_id=corpo.slot_id, agora=datetime.now(UTC),
            max_retries=state.settings.max_retries, idempotency_key=idempotency_key,
            correlation_id=request_id_var.get(),
        )
    except repo.SagaAtivaParaDoador:
        return problem(
            request, 409, "urn:startech:error:agendamento-ativo", "Agendamento em andamento",
            "O doador já possui uma solicitação de agendamento em andamento (RN09).",
        )
    saga = criacao.saga
    if not criacao.criada and (saga.doador_id, saga.slot_id) != (corpo.doador_id, corpo.slot_id):
        return problem(
            request, 422, "urn:startech:error:idempotency-key-reutilizada", "Idempotency-Key reutilizada",
            "Esta Idempotency-Key já foi usada em uma solicitação com outro doador ou slot.",
        )
    if criacao.criada:  # o passo 1 começa já; o worker de recuperação garante a retomada se algo falhar
        disparar(request.app, state.executor.avancar(saga.saga_id))
    resposta = dto.criada(saga)
    return JSONResponse(
        resposta.model_dump(mode="json", by_alias=True), status_code=status.HTTP_202_ACCEPTED,
        headers={"Location": dto.link_da_saga(saga.saga_id)},
    )


@router.get(
    "/{saga_id}",
    response_model=dto.SagaDetalhe,
    response_model_by_alias=True,
    responses={404: {"description": "SAGA inexistente"}},
)
async def consultar(request: Request, saga_id: uuid.UUID):
    """Estado atual, passos executados (ações positivas e compensações) e motivo de recusa, se houver."""
    sessoes = request.app.state.session_factory
    saga = await repo.obter(sessoes, saga_id)
    if saga is None:
        return problem(
            request, 404, "urn:startech:error:saga-nao-encontrada", "SAGA não encontrada",
            "Não existe SAGA com o identificador informado.",
        )
    return dto.detalhe(saga, await repo.listar_log(sessoes, saga_id))
