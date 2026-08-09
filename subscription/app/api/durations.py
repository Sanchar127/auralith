
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import get_current_user
from app.dependencies.duration import get_duration_service
from app.schemas.duration import (
    SubscriptionDurationCreate,
    SubscriptionDurationUpdate,
    SubscriptionDurationResponse,
)
from app.services.duration import SubscriptionDurationService


router = APIRouter(
    prefix="/durations",
    tags=["Subscription Durations"],
)


# ---------------------------------------------------------
# Create Duration
# ---------------------------------------------------------

@router.post(
    "",
    response_model=SubscriptionDurationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_duration(
    payload: SubscriptionDurationCreate,
    current_user=Depends(get_current_user),
    service: SubscriptionDurationService = Depends(
        get_duration_service,
    ),
):
    return await service.create_duration(payload)


# ---------------------------------------------------------
# List Durations
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[SubscriptionDurationResponse],
)
async def list_durations(
    active_only: bool = False,
    current_user=Depends(get_current_user),
    service: SubscriptionDurationService = Depends(
        get_duration_service,
    ),
):
    return await service.list_durations(
        active_only,
    )


# ---------------------------------------------------------
# Get Duration
# ---------------------------------------------------------

@router.get(
    "/{duration_id}",
    response_model=SubscriptionDurationResponse,
)
async def get_duration(
    duration_id: UUID,
    current_user=Depends(get_current_user),
    service: SubscriptionDurationService = Depends(
        get_duration_service,
    ),
):
    duration = await service.get_duration(
        duration_id,
    )

    if duration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duration not found",
        )

    return duration


# ---------------------------------------------------------
# Update Duration
# ---------------------------------------------------------

@router.patch(
    "/{duration_id}",
    response_model=SubscriptionDurationResponse,
)
async def update_duration(
    duration_id: UUID,
    payload: SubscriptionDurationUpdate,
    current_user=Depends(get_current_user),
    service: SubscriptionDurationService = Depends(
        get_duration_service,
    ),
):
    duration = await service.update_duration(
        duration_id,
        payload,
    )

    if duration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duration not found",
        )

    return duration


# ---------------------------------------------------------
# Delete Duration
# ---------------------------------------------------------

@router.delete(
    "/{duration_id}",
)
async def delete_duration(
    duration_id: UUID,
    current_user=Depends(get_current_user),
    service: SubscriptionDurationService = Depends(
        get_duration_service,
    ),
):
    deleted = await service.delete_duration(
        duration_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duration not found",
        )

    return {
        "message": "Duration deleted",
    }

