from fastapi import APIRouter

from config import settings
from schemas import HealthResponse


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    response_model=HealthResponse,
)
async def health_check():
    """
    Check service health.
    """

    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
    )