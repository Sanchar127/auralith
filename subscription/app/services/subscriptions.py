from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionPlan
from app.db.model.token_wallet import TokenWallet
from app.db.model.usersubscription import (
    SubscriptionStatus,
    UserSubscription,
)
from app.repositories.subscription import SubscriptionRepository
from app.exceptions import (
    SubscriptionAlreadyActiveError,
    SubscriptionNotFoundError,
)


class SubscriptionService:
    """
    Business logic for user subscriptions.

    Responsibilities:
    - Create subscriptions
    - Retrieve active subscriptions
    - Cancel subscriptions
    - Manage token wallets
    - Provide subscription status for gRPC
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SubscriptionRepository(db)

    # =========================================================
    # QUERIES
    # =========================================================

    async def get_active_subscription(
        self,
        user_id: uuid.UUID,
    ) -> UserSubscription | None:
        return await self.repo.get_active_subscription(
            user_id
        )

    async def get_subscription_status(
        self,
        user_id: uuid.UUID,
    ) -> tuple[bool, int]:
        """
        Used by the subscription gRPC service.

        Returns:
            (
                subscription_active,
                remaining_tokens,
            )
        """

        subscription = (
            await self.repo.get_active_subscription(
                user_id
            )
        )

        if subscription is None:
            return False, 0

        wallet = await self.repo.get_wallet(
            user_id
        )

        if wallet is None:
            return False, 0

        return (
            True,
            wallet.available_tokens,
        )

    async def list_subscriptions(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[SubscriptionStatus] = None,
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
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    # =========================================================
    # CREATE SUBSCRIPTION
    # =========================================================

    async def create_subscription(
        self,
        user_id: uuid.UUID,
        price_id: uuid.UUID,
    ) -> UserSubscription:

        # -----------------------------------------------------
        # 1. Check existing subscription
        # -----------------------------------------------------

        existing = (
            await self.repo.get_active_subscription(
                user_id
            )
        )

        if existing is not None:
            raise SubscriptionAlreadyActiveError(
                "User already has an active subscription."
            )

        # -----------------------------------------------------
        # 2. Load subscription plan
        # -----------------------------------------------------

        plan = await self.repo.get_price(
            price_id
        )

        if plan is None:
            raise SubscriptionNotFoundError(
                "Subscription plan not found."
            )

        # -----------------------------------------------------
        # 3. Validate plan
        # -----------------------------------------------------

        if not plan.is_active:
            raise SubscriptionNotFoundError(
                "Subscription plan is not active."
            )

        # -----------------------------------------------------
        # 4. Validate duration
        # -----------------------------------------------------

        if plan.duration is None:
            raise SubscriptionNotFoundError(
                "Subscription plan has no duration configured."
            )

        if plan.duration.duration_months <= 0:
            raise ValueError(
                "Subscription duration must be greater than zero."
            )

        # -----------------------------------------------------
        # 5. Calculate subscription dates
        # -----------------------------------------------------

        now = datetime.now(timezone.utc)

        expires_at = self.calculate_expiry(
            start=now,
            duration_months=(
                plan.duration.duration_months
            ),
        )

        # -----------------------------------------------------
        # 6. Create subscription
        # -----------------------------------------------------

        subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        starts_at=now,
        expires_at=expires_at,
    )

        await self.repo.create_subscription(
            subscription
        )

        # -----------------------------------------------------
        # 7. Create / update token wallet
        # -----------------------------------------------------

        await self.create_wallet(
            user_id=user_id,
            tokens=plan.monthly_tokens,
        )

        # -----------------------------------------------------
        # 8. Commit transaction
        # -----------------------------------------------------

        await self.repo.commit()

        await self.repo.refresh(
            subscription
        )

        return subscription

    # =========================================================
    # CANCEL
    # =========================================================

    async def cancel_subscription(
        self,
        user_id: uuid.UUID,
    ) -> UserSubscription | None:

        subscription = (
            await self.repo.get_active_subscription(
                user_id
            )
        )

        if subscription is None:
            return None

        subscription.status = (
            SubscriptionStatus.CANCELLED
        )

        await self.repo.commit()

        return subscription

    # =========================================================
    # TOKEN MANAGEMENT
    # =========================================================

    async def consume_tokens(
        self,
        user_id: uuid.UUID,
        amount: int,
    ) -> bool:
        """
        Consume tokens from user's wallet.

        Returns False if:
        - wallet doesn't exist
        - insufficient tokens
        """

        if amount <= 0:
            raise ValueError(
                "Token amount must be greater than zero."
            )

        wallet = await self.repo.get_wallet(
            user_id
        )

        if wallet is None:
            return False

        if wallet.available_tokens < amount:
            return False

        wallet.available_tokens -= amount
        wallet.used_tokens += amount

        await self.repo.commit()

        return True

    async def add_tokens(
        self,
        user_id: uuid.UUID,
        amount: int,
    ) -> None:

        if amount <= 0:
            raise ValueError(
                "Token amount must be greater than zero."
            )

        wallet = await self.repo.get_wallet(
            user_id
        )

        if wallet is None:

            wallet = TokenWallet(
                user_id=user_id,
                available_tokens=amount,
                used_tokens=0,
            )

            await self.repo.create_wallet(
                wallet
            )

        else:

            wallet.available_tokens += amount

        await self.repo.commit()

    async def create_wallet(
        self,
        user_id: uuid.UUID,
        tokens: int,
    ) -> TokenWallet:

        if tokens < 0:
            raise ValueError(
                "Token amount cannot be negative."
            )

        wallet = await self.repo.get_wallet(
            user_id
        )

        if wallet is not None:

            wallet.available_tokens += tokens

            return wallet

        wallet = TokenWallet(
            user_id=user_id,
            available_tokens=tokens,
            used_tokens=0,
        )

        return await self.repo.create_wallet(
            wallet
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def calculate_expiry(
        start: datetime,
        duration_months: int,
    ) -> datetime:
        """
        Calculate subscription expiry.

        Uses calendar month arithmetic rather than treating
        every month as exactly 30 days.
        """

        if duration_months <= 0:
            raise ValueError(
                "duration_months must be greater than zero."
            )

        month = (
            start.month - 1
            + duration_months
        )

        year = (
            start.year
            + month // 12
        )

        month = (
            month % 12
        ) + 1

        # Handle dates such as Jan 31 -> Feb 28/29.
        import calendar

        day = min(
            start.day,
            calendar.monthrange(
                year,
                month,
            )[1],
        )

        return start.replace(
            year=year,
            month=month,
            day=day,
        )