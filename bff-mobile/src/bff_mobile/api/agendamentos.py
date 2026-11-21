"""Agendamento de doação pelo app: inicia a SAGA no ms-orquestrador e acompanha o andamento (ADR-006).

- `POST /bff-mobile/agendamentos` {slotId}: o doador é o usuário autenticado (`X-User-Id` do Gateway).
  Responde 202 com o link de acompanhamento; repassa 409 (RN09) e 422 (Idempotency-Key reutilizada).
- `GET /bff-mobile/sagas/{sagaId}`: visão compacta para a tela do app. Só o próprio doador vê a sua SAGA
  (de outro doador responde 404, sem revelar que ela existe). Confirmada, traz o link `agendamento`.
- `GET /bff-mobile/agendamentos`, `GET /bff-mobile/agendamentos/{id}` e
  `POST /bff-mobile/agendamentos/{id}/cancelamento`: recurso Agendamento do `ms-agendamentos` com HATEOAS
  (contratos §3). Os links internos (`/api/v1/...`) são reescritos para as rotas públicas do Gateway
  (`/api/mobile/...`); links sem rota pública correspondente são descartados. Agendamento de outro doador
  responde 404.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from bff_mobile.autorizacao import exigir_papel
from bff_mobile.clients.servicos import AgendamentosClient, OrquestradorClient, ServicoIndisponivel
from bff_mobile.config import get_settings

router = APIRouter(prefix="/bff-mobile", tags=["agendamentos"], dependencies=[Depends(exigir_papel)])

PROBLEM_JSON = "application/problem+json"

# Status da SAGA -> situação exibida no app
_SITUACAO = {
    "CONFIRMED": "CONFIRMADO",
    "REJECTED": "RECUSADO",
    "COMPENSATED": "CANCELADO",
    "COMPENSATION_FAILED": "ERRO",
}


class SolicitacaoAgendamento(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slot_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)] = Field(
        alias="slotId", examples=["slot-20261125-1400"]
    )


class SolicitacaoCancelamento(BaseModel):
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None


def get_orquestrador(request: Request) -> OrquestradorClient:
    return request.app.state.orquestrador_client


def get_agendamentos(request: Request) -> AgendamentosClient:
    return request.app.state.agendamentos_client


def _problema(request: Request, status: int, tipo: str, titulo: str, detalhe: str) -> JSONResponse:
    corpo = {"type": f"urn:startech:error:{tipo}", "title": titulo, "status": status, "detail": detalhe,
             "instance": request.url.path}
    return JSONResponse(corpo, status_code=status, media_type=PROBLEM_JSON)


def _sem_usuario(request: Request) -> JSONResponse:
    return _problema(
        request, 401, "usuario-nao-identificado", "Usuário não identificado", "Cabeçalho X-User-Id ausente."
    )


def _indisponivel(request: Request, exc: ServicoIndisponivel) -> JSONResponse:
    return _problema(
        request, 503, "servico-indisponivel", "Agendamento temporariamente indisponível",
        f"Não foi possível falar com o serviço de agendamento ({exc.motivo}). Tente novamente.",
    )


def _repassar_problema(status: int, corpo: dict) -> JSONResponse:
    return JSONResponse(corpo, status_code=status, media_type=PROBLEM_JSON)


def _link_saga(saga_id: str) -> str:
    return f"{get_settings().prefixo_publico}/sagas/{saga_id}"


def _link_agendamento(agendamento_id: str) -> str:
    return f"{get_settings().prefixo_publico}/agendamentos/{agendamento_id}"


def _href_publico(href: str) -> str | None:
    """Rota interna do ms-agendamentos -> rota pública do Gateway; None se não houver rota pública."""
    prefixo = get_settings().prefixo_publico
    if href == "/api/v1/sagas/agendamento":  # novo agendamento = nova SAGA, que o app inicia pelo BFF
        return f"{prefixo}/agendamentos"
    if href.startswith("/api/v1/agendamentos/"):
        return f"{prefixo}/agendamentos/{href.removeprefix('/api/v1/agendamentos/')}"
    return None


def _agendamento_publico(agendamento: dict) -> dict:
    links: dict[str, Any] = {}
    for nome, link in (agendamento.get("_links") or {}).items():
        href = _href_publico(link.get("href", "")) if isinstance(link, dict) else None
        if href is not None:
            links[nome] = {**link, "href": href}
    return {**agendamento, "_links": links}


def _agendamento_nao_encontrado(request: Request) -> JSONResponse:
    return _problema(request, 404, "agendamento-nao-encontrado", "Agendamento não encontrado",
                     "Não existe agendamento com este identificador para o usuário.")


async def _agendamento_do_usuario(
    request: Request, agendamentos: AgendamentosClient, agendamento_id: str, user_id: str
) -> dict | JSONResponse:
    """O agendamento, se existir e for do usuário; senão a resposta de erro a devolver."""
    try:
        status, agendamento = await agendamentos.consultar(agendamento_id)
    except ServicoIndisponivel as exc:
        return _indisponivel(request, exc)
    if status in (400, 404) or (status == 200 and agendamento.get("doadorId") != user_id):
        return _agendamento_nao_encontrado(request)
    if status != 200:
        return _repassar_problema(status, agendamento)
    return agendamento


@router.post("/agendamentos", status_code=202)
async def solicitar_agendamento(
    request: Request,
    corpo: SolicitacaoAgendamento,
    orquestrador: Annotated[OrquestradorClient, Depends(get_orquestrador)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
):
    if not x_user_id:
        return _sem_usuario(request)
    try:
        status, resposta = await orquestrador.iniciar_agendamento(x_user_id, corpo.slot_id, idempotency_key)
    except ServicoIndisponivel as exc:
        return _indisponivel(request, exc)
    if status != 202:
        return _repassar_problema(status, resposta)
    link = _link_saga(resposta["sagaId"])
    return JSONResponse(
        {"sagaId": resposta["sagaId"], "agendamentoId": resposta["agendamentoId"], "situacao": "EM_ANDAMENTO",
         "_links": {"acompanhar": {"href": link, "method": "GET"}}},
        status_code=202, headers={"Location": link},
    )


@router.get("/sagas/{saga_id}")
async def acompanhar_agendamento(
    request: Request,
    saga_id: str,
    orquestrador: Annotated[OrquestradorClient, Depends(get_orquestrador)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    if not x_user_id:
        return _sem_usuario(request)
    try:
        status, saga = await orquestrador.consultar(saga_id)
    except ServicoIndisponivel as exc:
        return _indisponivel(request, exc)
    if status in (400, 404) or (status == 200 and saga.get("doadorId") != x_user_id):
        return _problema(request, 404, "agendamento-nao-encontrado", "Solicitação não encontrada",
                         "Não existe solicitação de agendamento com este identificador para o usuário.")
    if status != 200:
        return _repassar_problema(status, saga)
    recusa: dict[str, Any] = saga.get("recusa") or {}
    corpo: dict[str, Any] = {
        "sagaId": saga["sagaId"],
        "agendamentoId": saga["agendamentoId"],
        "situacao": _SITUACAO.get(saga["status"], "EM_ANDAMENTO"),
        "finalizada": saga["finalizada"],
        "slotId": saga["slotId"],
        "dataHoraInicio": saga.get("dataHoraInicio"),
        "motivo": recusa.get("detail") or recusa.get("title"),
        "_links": {"self": {"href": _link_saga(saga["sagaId"]), "method": "GET"}},
    }
    if saga["status"] == "CONFIRMED":
        corpo["_links"]["agendamento"] = {"href": _link_agendamento(saga["agendamentoId"]), "method": "GET"}
    if saga["status"] in ("REJECTED", "COMPENSATED"):
        novo = f"{get_settings().prefixo_publico}/agendamentos"
        corpo["_links"]["novo-agendamento"] = {"href": novo, "method": "POST"}
    return corpo


@router.get("/agendamentos")
async def listar_agendamentos(
    request: Request,
    agendamentos: Annotated[AgendamentosClient, Depends(get_agendamentos)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    if not x_user_id:
        return _sem_usuario(request)
    try:
        status, lista = await agendamentos.listar(x_user_id)
    except ServicoIndisponivel as exc:
        return _indisponivel(request, exc)
    if status != 200:
        return _repassar_problema(status, lista)
    prefixo = get_settings().prefixo_publico
    return {
        "itens": [_agendamento_publico(a) for a in lista.get("itens", []) if a.get("doadorId") == x_user_id],
        "_links": {"self": {"href": f"{prefixo}/agendamentos", "method": "GET"},
                   "novo-agendamento": {"href": f"{prefixo}/agendamentos", "method": "POST"}},
    }


@router.get("/agendamentos/{agendamento_id}")
async def consultar_agendamento(
    request: Request,
    agendamento_id: str,
    agendamentos: Annotated[AgendamentosClient, Depends(get_agendamentos)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    if not x_user_id:
        return _sem_usuario(request)
    resultado = await _agendamento_do_usuario(request, agendamentos, agendamento_id, x_user_id)
    if isinstance(resultado, JSONResponse):
        return resultado
    return _agendamento_publico(resultado)


@router.post("/agendamentos/{agendamento_id}/cancelamento")
async def cancelar_agendamento(
    request: Request,
    agendamento_id: str,
    agendamentos: Annotated[AgendamentosClient, Depends(get_agendamentos)],
    corpo: SolicitacaoCancelamento | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
):
    if not x_user_id:
        return _sem_usuario(request)
    # confere o dono antes de cancelar: o ms-agendamentos é interno e não conhece o usuário autenticado
    resultado = await _agendamento_do_usuario(request, agendamentos, agendamento_id, x_user_id)
    if isinstance(resultado, JSONResponse):
        return resultado
    try:
        status, cancelado = await agendamentos.cancelar(agendamento_id, corpo.motivo if corpo else None)
    except ServicoIndisponivel as exc:
        return _indisponivel(request, exc)
    if status == 404:
        return _agendamento_nao_encontrado(request)
    if status != 200:
        return _repassar_problema(status, cancelado)  # 409: já cancelado, ainda provisório ou fora do prazo
    return _agendamento_publico(cancelado)
