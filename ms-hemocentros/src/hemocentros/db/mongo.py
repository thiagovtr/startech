from pymongo import AsyncMongoClient

from hemocentros.config import Settings


def create_client(settings: Settings) -> AsyncMongoClient:
    # Conexão preguiçosa: o cliente não falha se o MongoDB estiver indisponível.
    timeout_ms = int(settings.db_check_timeout * 1000)
    return AsyncMongoClient(
        settings.mongo_url,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
    )


COLECAO_CAMPANHAS_VIEW = "campanhas_view"


async def garantir_indices(client: AsyncMongoClient, db_name: str) -> None:
    """Índice por tipo sanguíneo para a leitura da view CQRS (idempotente)."""
    await client[db_name][COLECAO_CAMPANHAS_VIEW].create_index("tipo_sanguineo")
