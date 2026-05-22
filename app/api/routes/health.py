from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "cropflow",
        "status": "ok",
        "environment": settings.environment,
    }
