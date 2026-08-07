from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionPlan


class SubscriptionPlanRepository:
    """
    Database operations for subscription plans.
    """

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


    async def get_plan_by_id(
        self,
        plan_id: uuid.UUID,
    ) -> SubscriptionPlan | None:

        result = await self.db.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.id == plan_id
            )
        )

        return result.scalar_one_or_none()



    async def get_plan_by_name(
        self,
        name: str,
    ) -> SubscriptionPlan | None:

        result = await self.db.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.name == name
            )
        )

        return result.scalar_one_or_none()



    async def get_all_plans(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SubscriptionPlan]:

        result = await self.db.execute(
            select(SubscriptionPlan)
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().all())



    async def get_active_plans(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SubscriptionPlan]:

        result = await self.db.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.is_active.is_(True)
            )
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().all())



    async def create_plan(
        self,
        plan: SubscriptionPlan,
    ) -> SubscriptionPlan:

        self.db.add(plan)

        await self.db.flush()

        return plan



    async def delete_plan(
        self,
        plan: SubscriptionPlan,
    ) -> None:

        await self.db.delete(plan)



    async def commit(
        self,
    ) -> None:

        await self.db.commit()



    async def refresh(
        self,
        obj,
    ) -> None:

        await self.db.refresh(obj)