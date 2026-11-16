"""Mensagens que a SAGA grava no Outbox: routing key, message_id e corpo (contratos §2.1)."""

from datetime import datetime
from typing import Any

from orquestrador.saga.estados import TipoMensagem

# tipo -> (routing key, sufixo do message_id `saga-{sagaId}-{sufixo}`)
ROTAS: dict[TipoMensagem, tuple[str, str]] = {
    TipoMensagem.PROGRAMAR_LEMBRETE: ("saga.comando.comunicacao.programar-lembrete", "step3"),
    TipoMensagem.CANCELAR_LEMBRETE: ("saga.comando.comunicacao.cancelar-lembrete", "step3-comp"),
    TipoMensagem.AGENDAMENTO_CONFIRMADO: ("saga.agendamento.confirmado", "desfecho"),
    TipoMensagem.AGENDAMENTO_COMPENSADO: ("saga.agendamento.compensado", "desfecho"),
    TipoMensagem.COMPENSACAO_FALHOU: ("saga.compensacao.falhou", "comp-falhou"),
}


def montar(
    tipo: TipoMensagem,
    *,
    saga_id: object,
    agendamento_id: str,
    doador_id: str,
    slot_id: str,
    payload: dict[str, Any],
    status: str,
    detalhe: str | None,
    agora: datetime,
) -> tuple[str, str, dict[str, Any]]:
    """Devolve (routing_key, message_id, corpo) da mensagem."""
    routing_key, sufixo = ROTAS[tipo]
    base = {"sagaId": str(saga_id), "agendamentoId": agendamento_id, "doadorId": doador_id}
    emitido = agora.isoformat().replace("+00:00", "Z")
    corpo: dict[str, Any]
    if tipo == TipoMensagem.PROGRAMAR_LEMBRETE:
        corpo = {"tipo": "ProgramarLembreteEConfirmar", **base, "slotId": slot_id,
                 "dataHoraInicio": payload.get("dataHoraInicio"), "emitidoEm": emitido}
    elif tipo == TipoMensagem.CANCELAR_LEMBRETE:
        corpo = {"tipo": "CancelarLembreteAgendado", **base, "emitidoEm": emitido}
    else:  # eventos de desfecho
        corpo = {**base, "status": status, "detalhe": detalhe, "emitidoEm": emitido}
    return routing_key, f"saga-{saga_id}-{sufixo}", corpo
