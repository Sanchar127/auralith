from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

from app.services.duration import (
    SubscriptionDurationService,
)


async def get_duration_service(
    db: AsyncSession = Depends(get_db),
):

    return SubscriptionDurationService(
        db
    )