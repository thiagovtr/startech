from fastapi import APIRouter

router = APIRouter(prefix="/bff-web", tags=["campanhas"])


@router.get("/campanhas")
def listar_campanhas() -> dict:
    """Mock fixo; a agregação real via ms-hemocentros vem no Bloco 17."""
    return {
        "status": "ok",
        "campanhas": [
            {"id": "camp-001", "titulo": "Alerta crítico: sangue O-", "tipo_sanguineo": "O-", "status": "ATIVA"},
            {"id": "camp-002", "titulo": "Campanha de fim de ano", "tipo_sanguineo": "A+", "status": "ATIVA"},
        ],
    }
