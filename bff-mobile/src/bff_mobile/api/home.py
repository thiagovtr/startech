from fastapi import APIRouter

router = APIRouter(prefix="/bff-mobile", tags=["home"])


@router.get("/home")
def home() -> dict:
    """Mock fixo; a agregação real (doadores + hemocentros) vem no Bloco 16."""
    return {
        "status": "ok",
        "doador": {"id": "123", "nome": "Doador Exemplo", "tipo_sanguineo": "O-", "elegivel": True},
        "campanhas": [
            {"id": "camp-001", "titulo": "Alerta crítico: sangue O-",
            "hemocentro": "Hemocentro Regional de Lavras", "tipo_sanguineo": "O-"},
        ],
    }
