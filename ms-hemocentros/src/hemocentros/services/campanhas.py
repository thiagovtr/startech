from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hemocentros.models.campanha import CampanhaAtualizar, CampanhaCriar
from hemocentros.models.orm import CampanhaModel, OutboxEvent
from hemocentros.observabilidade import request_id_var

ROUTING_KEY_CAMPANHA_CRIADA = "hemocentros.campanha.criada"
ROUTING_KEY_CAMPANHA_ATUALIZADA = "hemocentros.campanha.atualizada"


class CampanhaNaoEncontrada(Exception):
    """Campanha solicitada não existe no banco de escrita."""

    def __init__(self, campanha_id: str):
        super().__init__(f"Campanha '{campanha_id}' não encontrada.")
        self.campanha_id = campanha_id


def _payload_evento(campanha: CampanhaModel) -> dict:
    return {
        "id": campanha.id,
        "titulo": campanha.titulo,
        "hemocentro": campanha.hemocentro,
        "tipo_sanguineo": campanha.tipo_sanguineo,
        "urgencia": campanha.urgencia,
        "status": campanha.status,
        "data_inicio": campanha.data_inicio.isoformat(),
        "data_fim": campanha.data_fim.isoformat(),
        "versao": campanha.versao,
    }


async def criar_campanha(factory: async_sessionmaker[AsyncSession], dados: CampanhaCriar) -> CampanhaModel:
    """Grava a campanha e o evento `campanha.criada` na MESMA transação (Transactional Outbox)."""
    campanha = CampanhaModel(**dados.model_dump(), status="ATIVA")
    async with factory() as session, session.begin():
        session.add(campanha)
        session.add(
            OutboxEvent(
                aggregate_type="Campanha",
                aggregate_id=campanha.id,
                routing_key=ROUTING_KEY_CAMPANHA_CRIADA,
                payload=_payload_evento(campanha),
                correlation_id=request_id_var.get(),
            )
        )
    return campanha


async def atualizar_campanha(
    factory: async_sessionmaker[AsyncSession], campanha_id: str, dados: CampanhaAtualizar
) -> CampanhaModel:
    """Atualiza a campanha no PostgreSQL, incrementa `versao` e publica `campanha.atualizada` no Outbox."""
    async with factory() as session, session.begin():
        campanha = await session.get(CampanhaModel, campanha_id)
        if campanha is None:
            raise CampanhaNaoEncontrada(campanha_id)
        campanha.titulo = dados.titulo
        campanha.hemocentro = dados.hemocentro
        campanha.tipo_sanguineo = dados.tipo_sanguineo
        campanha.urgencia = dados.urgencia
        campanha.data_inicio = dados.data_inicio
        campanha.data_fim = dados.data_fim
        if dados.status is not None:
            campanha.status = dados.status
        campanha.versao = (campanha.versao or 1) + 1
        session.add(
            OutboxEvent(
                aggregate_type="Campanha",
                aggregate_id=campanha.id,
                routing_key=ROUTING_KEY_CAMPANHA_ATUALIZADA,
                payload=_payload_evento(campanha),
                correlation_id=request_id_var.get(),
            )
        )
    return campanha
