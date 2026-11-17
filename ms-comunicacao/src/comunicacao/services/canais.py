"""Canais de entrega das notificações.

O envio real (push, e-mail, SMS) está fora do escopo da disciplina: o canal `LOG` registra a notificação em
log estruturado. Toda notificação também fica no histórico (`notificacoes`), gravado na mesma transação da
mudança que a originou; o "envio" acontece depois do commit, para não registrar envio de algo que não persistiu.
"""

import logging

from comunicacao.models.orm import Notificacao

logger = logging.getLogger("ms-comunicacao.envio")

CANAL_PADRAO = "LOG"


def enviar(notificacao: Notificacao) -> None:
    logger.info(
        "[%s] %s -> doador %s: %s", notificacao.canal, notificacao.tipo, notificacao.doador_id or "*",
        notificacao.conteudo,
    )
