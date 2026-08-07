from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionPlan

from app.exceptions import (
    SubscriptionPlanAlreadyExistsError,
    SubscriptionPlanNotFoundError,
)

from app.repositories.plans import (
    SubscriptionPlanRepository,
)

from app.schemas.plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
)


class SubscriptionPlanService:
    """
    Service responsible for Subscription Plan CRUD.

    Handles:
    - Create subscription plan
    - Read subscription plans
    - Update subscription plans
    - Delete subscription plans
    - Activate / deactivate plans
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:

        self.repo = SubscriptionPlanRepository(db)


    # =====================================================
    # GET SINGLE PLAN
    # =====================================================

    async def get_plan(
        self,
        plan_id: uuid.UUID,
    ) -> SubscriptionPlan:

        plan = await self.repo.get_plan_by_id(
            plan_id
        )

        if plan is None:
            raise SubscriptionPlanNotFoundError(
                "Subscription plan not found."
            )

        return plan



    # =====================================================
    # LIST PLANS
    # =====================================================

    async def list_plans(
        self,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> list[SubscriptionPlan]:

        if active_only:
            return await self.repo.get_active_plans(
                skip=skip,
                limit=limit,
            )

        return await self.repo.get_all_plans(
            skip=skip,
            limit=limit,
        )

    # =====================================================
    # CREATE PLAN
    # =====================================================

    async def create_plan(
        self,
        payload: SubscriptionPlanCreate,
    ) -> SubscriptionPlan:


        existing = await self.repo.get_plan_by_name(
            payload.name
        )


        if existing:
            raise SubscriptionPlanAlreadyExistsError(
                "Subscription plan already exists."
            )


        plan = SubscriptionPlan(
            name=payload.name,
            description=payload.description,
            price=payload.price,
            monthly_tokens=payload.monthly_tokens,
            context_window=payload.context_window,
            duration_id=payload.duration_id,
            is_active=payload.is_active,
        )


        await self.repo.create_plan(
            plan
        )

        await self.repo.commit()

        await self.repo.refresh(
            plan
        )


        return plan



    # =====================================================
    # UPDATE PLAN
    # =====================================================

    async def update_plan(
        self,
        plan_id: uuid.UUID,
        payload: SubscriptionPlanUpdate,
    ) -> SubscriptionPlan:


        plan = await self.repo.get_plan_by_id(
            plan_id
        )


        if plan is None:
            raise SubscriptionPlanNotFoundError(
                "Subscription plan not found."
            )


        data = payload.model_dump(
            exclude_unset=True
        )


        for key,value in data.items():

            setattr(
                plan,
                key,
                value
            )


        await self.repo.commit()

        await self.repo.refresh(
            plan
        )


        return plan



    # =====================================================
    # DELETE PLAN
    # =====================================================

    async def delete_plan(
        self,
        plan_id: uuid.UUID,
    ) -> None:


        plan = await self.repo.get_plan_by_id(
            plan_id
        )


        if plan is None:
            raise SubscriptionPlanNotFoundError(
                "Subscription plan not found."
            )


        await self.repo.delete_plan(
            plan
        )


        await self.repo.commit()



    # =====================================================
    # ENABLE PLAN
    # =====================================================

    async def activate_plan(
        self,
        plan_id: uuid.UUID,
    ) -> SubscriptionPlan:


        plan = await self.get_plan(
            plan_id
        )


        plan.is_active = True


        await self.repo.commit()

        await self.repo.refresh(
            plan
        )


        return plan



    # =====================================================
    # DISABLE PLAN
    # =====================================================

    async def deactivate_plan(
        self,
        plan_id: uuid.UUID,
    ) -> SubscriptionPlan:


        plan = await self.get_plan(
            plan_id
        )


        plan.is_active = False


        await self.repo.commit()

        await self.repo.refresh(
            plan
        )


        return plan