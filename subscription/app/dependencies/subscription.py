from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.session import get_db
from app.services.subscriptions import SubscriptionService


async def get_subscription_service(
    db: AsyncSession = Depends(get_db),
) -> SubscriptionService:
    return SubscriptionService(db)