"""Participante simulado do passo 2 da SAGA (ms-doadores, RN01) para o E2E e a demonstração.

Usado SÓ por scripts/e2e-saga.sh enquanto o endpoint real do ms-doadores (contratos §2) não existe; os passos
1 e 4 já são do ms-agendamentos real. Estado em memória e uma regra RN01 simplificada que casa com a grade do
perfil `demo` do ms-agendamentos:

- todo doador tem a última doação há 10 dias; o intervalo mínimo é de 60 dias;
- `slot-futuro*` (daqui a 90+ dias): doador apto -> SAGA confirmada;
- `slot-proximo` (daqui a 7 dias): doador inapto (RN01, 422) -> vaga liberada e SAGA compensada.

`GET /fake/estado` mostra as travas e as chamadas recebidas, para o roteiro conferir as compensações.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import FastAPI, Header, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="participantes-fake")

AGORA = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
ULTIMA_DOACAO = AGORA - timedelta(days=10)
INTERVALO_MINIMO = timedelta(days=60)

TRAVAS: dict[str, dict[str, Any]] = {}  # agendamentoId -> trava temporal do doador
CHAMADAS: list[str] = []


def _problema(status: int, tipo: str, titulo: str, detalhe: str, **extra) -> JSONResponse:
    corpo = {"type": f"urn:startech:error:{tipo}", "title": titulo, "status": status, "detail": detalhe, **extra}
    return JSONResponse(corpo, status_code=status, media_type="application/problem+json")


def _registrar(chamada: str, chave: str | None) -> None:
    CHAMADAS.append(f"{chamada} [Idempotency-Key: {chave}]")


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
        "travas": TRAVAS,
        "chamadas": CHAMADAS,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
