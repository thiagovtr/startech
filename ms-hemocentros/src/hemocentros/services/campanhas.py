from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hemocentros.models.campanha import CampanhaCriar
from hemocentros.models.orm import CampanhaModel, OutboxEvent

ROUTING_KEY_CAMPANHA_CRIADA = "hemocentros.campanha.criada"


async def criar_campanha(factory: async_sessionmaker[AsyncSession], dados: CampanhaCriar) -> CampanhaModel:
    """Grava a campanha e o evento `campanha.criada` na MESMA transação (Transactional Outbox)."""
    campanha = CampanhaModel(**dados.model_dump(), status="ATIVA")
    payload = {
        "id": campanha.id,
        "titulo": campanha.titulo,
        "hemocentro": campanha.hemocentro,
        "tipo_sanguineo": campanha.tipo_sanguineo,
        "urgencia": campanha.urgencia,
        "status": campanha.status,
        "data_inicio": campanha.data_inicio.isoformat(),
        "data_fim": campanha.data_fim.isoformat(),
    }
    async with factory() as session, session.begin():
        session.add(campanha)
        session.add(
            OutboxEvent(
                aggregate_type="Campanha",
                aggregate_id=campanha.id,
                routing_key=ROUTING_KEY_CAMPANHA_CRIADA,
                payload=payload,
            )
        )
    return campanha
