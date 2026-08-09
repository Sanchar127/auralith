from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    Subscription business logic.

    Responsible for:

    - Creating subscriptions
    - Getting active subscriptions
    - Cancelling subscriptions
    - Managing token wallets
    - gRPC subscription validation
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.repo = SubscriptionRepository(db)
        self.db = db  # Add this line to access db directly

    # ---------------------------------------------------------
    # Queries
    # ---------------------------------------------------------

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
        Used by gRPC.

        Returns:
            (
                subscription_active,
                remaining_tokens,
            )
        """

        subscription = await self.repo.get_active_subscription(
            user_id
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

    # ADD THIS NEW METHOD
    async def list_subscriptions(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[SubscriptionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UserSubscription]:
        """
        List all subscriptions with optional filters.
        Used by admin endpoints.
        """
        query = select(UserSubscription)
        
        # Apply filters
        if user_id:
            query = query.where(UserSubscription.user_id == user_id)
        if status:
            query = query.where(UserSubscription.status == status)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    # ---------------------------------------------------------
    # Commands
    # ---------------------------------------------------------

    async def create_subscription(
        self,
        user_id: uuid.UUID,
        price_id: uuid.UUID,
    ) -> UserSubscription:

        existing = await self.repo.get_active_subscription(
            user_id
        )

        if existing:
            raise SubscriptionAlreadyActiveError(
                "User already has an active subscription."
            )

        price = await self.repo.get_price(
            price_id
        )

        if price is None:
            raise SubscriptionNotFoundError(
                "Subscription plan not found."
            )

        now = datetime.now(
            timezone.utc
        )

        subscription = UserSubscription(
            user_id=user_id,
            plan_id=price.plan_id,
            subscription_price_id=price.id,
            status=SubscriptionStatus.ACTIVE,
            starts_at=now,
            expires_at=self.calculate_expiry(
                now,
                price.billing_interval,
            ),
            auto_renew=False,
        )

        await self.repo.create_subscription(
            subscription
        )

        await self.create_wallet(
            user_id=user_id,
            tokens=price.plan.monthly_token_quota,
        )

        await self.repo.commit()

        await self.repo.refresh(
            subscription
        )

        return subscription

    async def cancel_subscription(
        self,
        user_id: uuid.UUID,
    ) -> UserSubscription | None:

        subscription = await self.repo.get_active_subscription(
            user_id
        )

        if subscription is None:
            return None

        subscription.status = (
            SubscriptionStatus.CANCELLED
        )

        await self.repo.commit()

        return subscription

    async def consume_tokens(
        self,
        user_id: uuid.UUID,
        amount: int,
    ) -> bool:
        """
        Called after successful AI generation.

        Returns False if insufficient tokens.
        """

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

        wallet = await self.repo.get_wallet(
            user_id
        )

        if wallet:

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

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def calculate_expiry(
        start: datetime,
        interval: str,
    ) -> datetime:

        durations = {
            "monthly": 30,
            "3_month": 90,
            "6_month": 180,
            "yearly": 365,
        }

        days = durations.get(interval)

        if days is None:
            raise ValueError(
                f"Invalid billing interval: {interval}"
            )

        return start + timedelta(
            days=days
        )