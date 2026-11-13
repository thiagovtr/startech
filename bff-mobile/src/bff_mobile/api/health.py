from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Readiness: o BFF não tem banco nem estado; serviço interno fora é tratado por degradação, não por readiness."""
    return {"status": "ok"}
