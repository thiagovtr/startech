"""ms-doadores: passo 2 (reservar/liberar elegibilidade, RN01). Contratos §2."""

import httpx

from orquestrador.clients.base import ClienteParticipante, Resultado, chave


class DoadoresClient:
    def __init__(self, http: httpx.AsyncClient):
        self._cliente = ClienteParticipante(http, "ms-doadores")

    async def reservar_elegibilidade(
        self, saga_id: object, doador_id: str, agendamento_id: str, data_slot: str, correlation_id: str | None = None
    ) -> Resultado:
        """Passo 2: valida a RN01 e aplica a trava temporal (422 se o doador estiver inapto)."""
        return await self._cliente.chamar(
            "POST", f"/api/v1/doadores/{doador_id}/reservas-elegibilidade",
            corpo={"agendamentoId": agendamento_id, "dataSlot": data_slot},
            idempotency_key=chave(saga_id, 2), correlation_id=correlation_id,
        )

    async def liberar_elegibilidade(
        self, saga_id: object, doador_id: str, agendamento_id: str, correlation_id: str | None = None
    ) -> Resultado:
        """Compensação do passo 2 (idempotente: trava inexistente conta como liberada)."""
        return await self._cliente.chamar(
            "DELETE", f"/api/v1/doadores/{doador_id}/reservas-elegibilidade/{agendamento_id}",
            idempotency_key=chave(saga_id, 2, compensacao=True), correlation_id=correlation_id, compensacao=True,
        )
