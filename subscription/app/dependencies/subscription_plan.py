from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.plans import SubscriptionPlanService


async def get_subscription_plan_service(
    db: AsyncSession = Depends(get_db),
) -> SubscriptionPlanService:
    return SubscriptionPlanService(db)