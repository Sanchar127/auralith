from __future__ import annotations

import uuid

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionPlan
from app.db.model.usersubscription import (
    UserSubscription,
    SubscriptionStatus,
)
from app.db.model.token_wallet import TokenWallet


class SubscriptionRepository:
    """
    Handles subscription related database operations.
    """


    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


    async def get_active_subscription(
        self,
        user_id: uuid.UUID,
    ) -> UserSubscription | None:

        result = await self.db.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status
                == SubscriptionStatus.ACTIVE,
                UserSubscription.expires_at
                > datetime.now(timezone.utc),
            )
        )

        return result.scalar_one_or_none()



    async def get_price(
        self,
        price_id: uuid.UUID,
    ) -> SubscriptionPlan | None:

        result = await self.db.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.id == price_id
            )
        )

        return result.scalar_one_or_none()



    async def create_subscription(
        self,
        subscription: UserSubscription,
    ) -> UserSubscription:

        self.db.add(subscription)

        await self.db.flush()

        return subscription



    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
    ) -> UserSubscription | None:

        result = await self.db.execute(
            select(UserSubscription)
            .where(
                UserSubscription.id
                == subscription_id
            )
        )

        return result.scalar_one_or_none()



    async def get_wallet(
        self,
        user_id: uuid.UUID,
    ) -> TokenWallet | None:

        result = await self.db.execute(
            select(TokenWallet)
            .where(
                TokenWallet.user_id
                == user_id
            )
        )

        return result.scalar_one_or_none()



    async def create_wallet(
        self,
        wallet: TokenWallet,
    ) -> TokenWallet:

        self.db.add(wallet)

        await self.db.flush()

        return wallet



    async def commit(self):

        await self.db.commit()



    async def refresh(
        self,
        obj,
    ):

        await self.db.refresh(obj)


async def get_plan_by_id(
    self,
    plan_id: uuid.UUID,
) -> SubscriptionPlan | None:

    result = await self.db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == plan_id
        )
    )

    return result.scalar_one_or_none()


async def get_plan_by_name(
    self,
    name: str,
) -> SubscriptionPlan | None:

    result = await self.db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.name == name
        )
    )

    return result.scalar_one_or_none()


async def get_all_plans(
    self,
) -> list[SubscriptionPlan]:

    result = await self.db.execute(
        select(SubscriptionPlan)
    )

    return list(result.scalars().all())


async def get_active_plans(
    self,
) -> list[SubscriptionPlan]:

    result = await self.db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.is_active.is_(True)
        )
    )

    return list(result.scalars().all())


async def create_plan(
    self,
    plan: SubscriptionPlan,
):

    self.db.add(plan)
    await self.db.flush()

    return plan


async def delete_plan(
    self,
    plan: SubscriptionPlan,
):

    await self.db.delete(plan)