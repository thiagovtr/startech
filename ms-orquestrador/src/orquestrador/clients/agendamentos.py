"""ms-agendamentos: passo 1 (reservar/liberar vaga) e passo 4 (confirmar). Contratos §2."""

import httpx

from orquestrador.clients.base import ClienteParticipante, Falha, Resultado, Sucesso, chave


class AgendamentosClient:
    def __init__(self, http: httpx.AsyncClient):
        self._cliente = ClienteParticipante(http, "ms-agendamentos")

    async def reservar_vaga(
        self, saga_id: object, slot_id: str, agendamento_id: str, doador_id: str, correlation_id: str | None = None
    ) -> Resultado:
        """Passo 1. Sucesso traz `dataHoraInicio`/`dataHoraFim` do slot, usados nos passos 2 e 3."""
        resultado = await self._cliente.chamar(
            "POST", f"/api/v1/slots/{slot_id}/reservas",
            corpo={"agendamentoId": agendamento_id, "doadorId": doador_id},
            idempotency_key=chave(saga_id, 1), correlation_id=correlation_id,
        )
        if isinstance(resultado, Sucesso) and not resultado.dados.get("dataHoraInicio"):
            return Falha("ms-agendamentos: resposta da reserva sem dataHoraInicio")
        return resultado

    async def liberar_vaga(
        self, saga_id: object, slot_id: str, agendamento_id: str, correlation_id: str | None = None
    ) -> Resultado:
        """Compensação do passo 1 (idempotente: reserva inexistente conta como liberada)."""
        return await self._cliente.chamar(
            "DELETE", f"/api/v1/slots/{slot_id}/reservas/{agendamento_id}",
            idempotency_key=chave(saga_id, 1, compensacao=True), correlation_id=correlation_id, compensacao=True,
        )

    async def confirmar(self, saga_id: object, agendamento_id: str, correlation_id: str | None = None) -> Resultado:
        """Passo 4 (final): CRIADO_PROVISORIO -> CONFIRMADO."""
        return await self._cliente.chamar(
            "POST", f"/api/v1/agendamentos/{agendamento_id}/confirmacao",
            idempotency_key=chave(saga_id, 4), correlation_id=correlation_id,
        )
