from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.model.subscriptions import (
    SubscriptionPlan,
)
from app.db.model.usersubscription import (
    SubscriptionStatus,
    UserSubscription,
)
from app.db.model.token_wallet import (
    TokenWallet,
)


class SubscriptionRepository:
    """
    Repository for subscription-related database operations.

    Responsibilities:
    - Query subscriptions
    - Query subscription plans
    - Query subscription durations through eager loading
    - Create/update subscriptions
    - Manage token wallets
    - Manage subscription plans

    This repository is designed for SQLAlchemy AsyncSession.

    Important:
    Relationships that may be accessed outside the original
    query are eagerly loaded to avoid MissingGreenlet errors.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # =========================================================
    # SUBSCRIPTIONS
    # =========================================================

    async def get_active_subscription(
        self,
        user_id: uuid.UUID,
    ) -> UserSubscription | None:
        """
        Return the user's currently active and non-expired
        subscription.

        Returns:
            UserSubscription | None
        """

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

    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
    ) -> UserSubscription | None:
        """
        Get a subscription by ID.
        """

        result = await self.db.execute(
            select(UserSubscription)
            .where(
                UserSubscription.id == subscription_id,
            )
        )

        return result.scalar_one_or_none()

    async def create_subscription(
        self,
        subscription: UserSubscription,
    ) -> UserSubscription:
        """
        Add a subscription to the current transaction.

        The caller is responsible for commit/rollback.
        """

        self.db.add(subscription)

        await self.db.flush()

        return subscription

    async def list_subscriptions(
        self,
        user_id: uuid.UUID | None = None,
        status: SubscriptionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserSubscription]:
        """
        List subscriptions with optional filters.
        """

        query = select(UserSubscription)

        if user_id is not None:
            query = query.where(
                UserSubscription.user_id == user_id
            )

        if status is not None:
            query = query.where(
                UserSubscription.status == status
            )

        query = (
            query
            .order_by(
                UserSubscription.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)

        return list(
            result.scalars().all()
        )

    # =========================================================
    # SUBSCRIPTION PLANS
    # =========================================================

    async def get_price(
        self,
        price_id: uuid.UUID,
    ) -> SubscriptionPlan | None:
        """
        Get a subscription plan by ID.

        The duration relationship is eagerly loaded.

        This is important because SubscriptionPlan.duration
        is accessed by the service after this method returns.

        Without selectinload(), SQLAlchemy may attempt an
        implicit async DB query when plan.duration is accessed,
        causing:

            sqlalchemy.exc.MissingGreenlet
        """

        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(
                selectinload(
                    SubscriptionPlan.duration
                )
            )
            .where(
                SubscriptionPlan.id == price_id
            )
        )

        return result.scalar_one_or_none()

    async def get_plan_by_id(
        self,
        plan_id: uuid.UUID,
    ) -> SubscriptionPlan | None:
        """
        Get subscription plan by ID.

        Duration is eagerly loaded.
        """

        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(
                selectinload(
                    SubscriptionPlan.duration
                )
            )
            .where(
                SubscriptionPlan.id == plan_id
            )
        )

        return result.scalar_one_or_none()

    async def get_plan_by_name(
        self,
        name: str,
    ) -> SubscriptionPlan | None:
        """
        Get subscription plan by name.

        Duration is eagerly loaded.
        """

        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(
                selectinload(
                    SubscriptionPlan.duration
                )
            )
            .where(
                SubscriptionPlan.name == name
            )
        )

        return result.scalar_one_or_none()

    async def get_all_plans(
        self,
    ) -> list[SubscriptionPlan]:
        """
        Return all subscription plans.

        Duration is eagerly loaded.
        """

        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(
                selectinload(
                    SubscriptionPlan.duration
                )
            )
            .order_by(
                SubscriptionPlan.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    async def get_active_plans(
        self,
    ) -> list[SubscriptionPlan]:
        """
        Return active subscription plans.

        Duration is eagerly loaded.
        """

        result = await self.db.execute(
            select(SubscriptionPlan)
            .options(
                selectinload(
                    SubscriptionPlan.duration
                )
            )
            .where(
                SubscriptionPlan.is_active.is_(True)
            )
            .order_by(
                SubscriptionPlan.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    async def create_plan(
        self,
        plan: SubscriptionPlan,
    ) -> SubscriptionPlan:
        """
        Add a subscription plan to the current transaction.

        The caller is responsible for commit/rollback.
        """

        self.db.add(plan)

        await self.db.flush()

        return plan

    async def delete_plan(
        self,
        plan: SubscriptionPlan,
    ) -> None:
        """
        Delete a subscription plan.

        The caller is responsible for commit/rollback.
        """

        await self.db.delete(plan)

        await self.db.flush()

    # =========================================================
    # TOKEN WALLET
    # =========================================================

    async def get_wallet(
        self,
        user_id: uuid.UUID,
    ) -> TokenWallet | None:
        """
        Get user's token wallet.
        """

        result = await self.db.execute(
            select(TokenWallet)
            .where(
                TokenWallet.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def create_wallet(
        self,
        wallet: TokenWallet,
    ) -> TokenWallet:
        """
        Add a token wallet to the current transaction.
        """

        self.db.add(wallet)

        await self.db.flush()

        return wallet

    # =========================================================
    # TRANSACTION MANAGEMENT
    # =========================================================

    async def commit(self) -> None:
        """
        Commit current transaction.
        """

        await self.db.commit()

    async def rollback(self) -> None:
        """
        Roll back current transaction.
        """

        await self.db.rollback()

    async def refresh(
        self,
        obj,
    ) -> None:
        """
        Refresh an ORM object from the database.
        """

        await self.db.refresh(obj)