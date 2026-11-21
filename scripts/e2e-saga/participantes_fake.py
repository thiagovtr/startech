"""Participantes simulados da SAGA (ms-agendamentos e ms-doadores) para o E2E e a demonstração.

Usado SÓ por scripts/e2e-saga.sh enquanto os endpoints reais (contratos §2) não existem. Implementa os
contratos da SAGA com estado em memória e uma regra RN01 simplificada para provocar a compensação:

- todo doador tem a última doação há 10 dias; o intervalo mínimo é de 60 dias;
- `slot-futuro` (daqui a 90 dias): doador apto -> SAGA confirmada;
- `slot-proximo` (daqui a 7 dias): doador inapto (RN01, 422) -> vaga liberada e SAGA compensada;
- `slot-lotado` (capacidade 0): 409 no passo 1 -> SAGA recusada sem compensação.

Também expõe o recurso Agendamento com HATEOAS (contratos §3) com as mesmas regras do `ms-agendamentos`:
`GET /api/v1/agendamentos[?doadorId=]`, `GET /api/v1/agendamentos/{id}` e `POST .../{id}/cancelamento`
(só `CONFIRMADO` e até 2 h antes; cancelar de novo responde 409).

`GET /fake/estado` mostra vagas, agendamentos e travas, para o roteiro conferir o efeito das compensações.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Body, FastAPI, Header, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="participantes-fake")

AGORA = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
ULTIMA_DOACAO = AGORA - timedelta(days=10)
INTERVALO_MINIMO = timedelta(days=60)

SLOTS: dict[str, dict[str, Any]] = {
    "slot-futuro": {"inicio": AGORA + timedelta(days=90), "capacidade": 5, "ocupadas": 0},
    "slot-proximo": {"inicio": AGORA + timedelta(days=7), "capacidade": 5, "ocupadas": 0},
    "slot-lotado": {"inicio": AGORA + timedelta(days=30), "capacidade": 0, "ocupadas": 0},
}
AGENDAMENTOS: dict[str, dict[str, Any]] = {}
TRAVAS: dict[str, dict[str, Any]] = {}  # agendamentoId -> trava temporal do doador
CHAMADAS: list[str] = []


def _iso(d: datetime) -> str:
    return d.isoformat().replace("+00:00", "Z")


def _problema(status: int, tipo: str, titulo: str, detalhe: str, **extra) -> JSONResponse:
    corpo = {"type": f"urn:startech:error:{tipo}", "title": titulo, "status": status, "detail": detalhe, **extra}
    return JSONResponse(corpo, status_code=status, media_type="application/problem+json")


def _registrar(chamada: str, chave: str | None) -> None:
    CHAMADAS.append(f"{chamada} [Idempotency-Key: {chave}]")


# ------------------------------------------------------------------ ms-agendamentos


@app.post("/api/v1/slots/{slot_id}/reservas", status_code=201)
async def reservar_vaga(slot_id: str, corpo: dict, idempotency_key: Annotated[str | None, Header()] = None):
    _registrar(f"POST /slots/{slot_id}/reservas", idempotency_key)
    slot = SLOTS.get(slot_id)
    if slot is None:
        return _problema(404, "slot-nao-encontrado", "Slot não encontrado", f"Não existe o slot {slot_id}.")
    ag_id = corpo["agendamentoId"]
    existente = AGENDAMENTOS.get(ag_id)
    if existente is None:  # idempotente: a mesma reserva não ocupa duas vagas
        if slot["ocupadas"] >= slot["capacidade"]:
            return _problema(409, "slot-esgotado", "Slot esgotado", f"Não há vagas no slot {slot_id}.")
        slot["ocupadas"] += 1
        existente = {"slotId": slot_id, "doadorId": corpo["doadorId"], "status": "CRIADO_PROVISORIO",
                     "dataCancelamento": None, "motivo": None}
        AGENDAMENTOS[ag_id] = existente
    return {"agendamentoId": ag_id, "slotId": slot_id, "dataHoraInicio": _iso(slot["inicio"]),
            "dataHoraFim": _iso(slot["inicio"] + timedelta(minutes=20)), "status": existente["status"]}


@app.delete("/api/v1/slots/{slot_id}/reservas/{agendamento_id}", status_code=204)
async def liberar_vaga(slot_id: str, agendamento_id: str, idempotency_key: Annotated[str | None, Header()] = None):
    _registrar(f"DELETE /slots/{slot_id}/reservas/{agendamento_id}", idempotency_key)
    ag = AGENDAMENTOS.get(agendamento_id)
    if ag is not None and ag["status"] != "CANCELADO_COMPENSACAO_SAGA":  # idempotente
        SLOTS[ag["slotId"]]["ocupadas"] -= 1
        ag["status"] = "CANCELADO_COMPENSACAO_SAGA"
    return Response(status_code=204)


@app.post("/api/v1/agendamentos/{agendamento_id}/confirmacao")
async def confirmar(agendamento_id: str, idempotency_key: Annotated[str | None, Header()] = None):
    _registrar(f"POST /agendamentos/{agendamento_id}/confirmacao", idempotency_key)
    ag = AGENDAMENTOS.get(agendamento_id)
    if ag is None:
        return _problema(404, "agendamento-nao-encontrado", "Agendamento não encontrado", agendamento_id)
    ag["status"] = "CONFIRMADO"
    return {"id": agendamento_id, **ag}


ANTECEDENCIA_CANCELAMENTO = timedelta(hours=2)


def _representacao(ag_id: str, ag: dict[str, Any]) -> dict[str, Any]:
    inicio = SLOTS[ag["slotId"]]["inicio"]
    fim = inicio + timedelta(minutes=20)
    agora = datetime.now(UTC)
    base = f"/api/v1/agendamentos/{ag_id}"
    corpo: dict[str, Any] = {
        "id": ag_id, "status": ag["status"], "concluido": ag["status"] == "CONFIRMADO" and fim <= agora,
        "doadorId": ag["doadorId"],
        "slot": {"slotId": ag["slotId"], "postoId": "posto-fake", "dataHoraInicio": _iso(inicio),
                 "dataHoraFim": _iso(fim)},
    }
    links: dict[str, Any] = {"self": {"href": base, "method": "GET", "title": "Consultar dados do agendamento"}}
    if ag["status"].startswith("CANCELADO"):
        corpo.update(dataCancelamento=ag["dataCancelamento"], motivo=ag["motivo"], slotLiberado=ag["slotId"])
        links["novo-agendamento"] = {"href": "/api/v1/sagas/agendamento", "method": "POST",
                                     "title": "Solicitar um novo agendamento"}
    elif ag["status"] == "CONFIRMADO" and agora < inicio - ANTECEDENCIA_CANCELAMENTO:
        links["cancelar"] = {"href": f"{base}/cancelamento", "method": "POST",
                             "title": "Efetuar cancelamento e liberar vaga para outros doadores",
                             "conditions": "Permitido até 2 horas antes do horário agendado"}
    corpo["_links"] = links
    return corpo


@app.get("/api/v1/agendamentos")
async def listar_agendamentos(doadorId: str):  # noqa: N803 (nome do parâmetro do contrato)
    itens = [(k, v) for k, v in AGENDAMENTOS.items() if v["doadorId"] == doadorId]
    itens.sort(key=lambda kv: SLOTS[kv[1]["slotId"]]["inicio"], reverse=True)
    return {"itens": [_representacao(k, v) for k, v in itens],
            "_links": {"self": {"href": f"/api/v1/agendamentos?doadorId={doadorId}", "method": "GET"}}}


@app.get("/api/v1/agendamentos/{agendamento_id}")
async def consultar_agendamento(agendamento_id: str):
    ag = AGENDAMENTOS.get(agendamento_id)
    if ag is None:
        return _problema(404, "agendamento-nao-encontrado", "Agendamento não encontrado", agendamento_id)
    return _representacao(agendamento_id, ag)


@app.post("/api/v1/agendamentos/{agendamento_id}/cancelamento")
async def cancelar_agendamento(agendamento_id: str, corpo: Annotated[dict | None, Body()] = None):
    CHAMADAS.append(f"POST /agendamentos/{agendamento_id}/cancelamento")
    ag = AGENDAMENTOS.get(agendamento_id)
    if ag is None:
        return _problema(404, "agendamento-nao-encontrado", "Agendamento não encontrado", agendamento_id)
    if ag["status"].startswith("CANCELADO"):
        return _problema(409, "agendamento-ja-cancelado", "Agendamento já cancelado",
                         f"O agendamento {agendamento_id} já está {ag['status']}.")
    if ag["status"] != "CONFIRMADO":
        return _problema(409, "agendamento-nao-cancelavel", "Agendamento ainda em processamento", agendamento_id)
    if datetime.now(UTC) >= SLOTS[ag["slotId"]]["inicio"] - ANTECEDENCIA_CANCELAMENTO:
        return _problema(409, "prazo-cancelamento-expirado", "Prazo de cancelamento encerrado", agendamento_id)
    SLOTS[ag["slotId"]]["ocupadas"] -= 1
    ag.update(status="CANCELADO_DOADOR", dataCancelamento=_iso(datetime.now(UTC)),
              motivo=((corpo or {}).get("motivo") or "Cancelado pelo doador"))
    return _representacao(agendamento_id, ag)


# ------------------------------------------------------------------ ms-doadores


@app.post("/api/v1/doadores/{doador_id}/reservas-elegibilidade")
async def reservar_elegibilidade(doador_id: str, corpo: dict, idempotency_key: Annotated[str | None, Header()] = None):
    _registrar(f"POST /doadores/{doador_id}/reservas-elegibilidade", idempotency_key)
    data_slot = datetime.fromisoformat(corpo["dataSlot"].replace("Z", "+00:00"))
    liberacao = ULTIMA_DOACAO + INTERVALO_MINIMO
    if data_slot < liberacao:
        return _problema(
            422, "intervalo-minimo-nao-cumprido", "Doador inapto para a data escolhida",
            f"A última doação foi em {ULTIMA_DOACAO.date()} (há 10 dias). Conforme a Portaria MS nº 5/2017, "
            f"a próxima doação é permitida a partir de {liberacao.date()} (60 dias de intervalo).",
            invalidParams=[{"name": "dataSlot", "reason": f"{data_slot.date()} é anterior a {liberacao.date()}"}],
        )
    TRAVAS[corpo["agendamentoId"]] = {"doadorId": doador_id, "dataSlot": corpo["dataSlot"]}
    return {"doadorId": doador_id, "agendamentoId": corpo["agendamentoId"], "travado": True}


@app.delete("/api/v1/doadores/{doador_id}/reservas-elegibilidade/{agendamento_id}", status_code=204)
async def liberar_elegibilidade(
    doador_id: str, agendamento_id: str, idempotency_key: Annotated[str | None, Header()] = None
):
    _registrar(f"DELETE /doadores/{doador_id}/reservas-elegibilidade/{agendamento_id}", idempotency_key)
    TRAVAS.pop(agendamento_id, None)
    return Response(status_code=204)


# ------------------------------------------------------------------ apoio ao roteiro


@app.get("/fake/estado")
async def estado():
    return {
        "slots": {k: {"ocupadas": v["ocupadas"], "capacidade": v["capacidade"], "inicio": _iso(v["inicio"])}
                  for k, v in SLOTS.items()},
        "agendamentos": AGENDAMENTOS,
        "travas": TRAVAS,
        "chamadas": CHAMADAS,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
