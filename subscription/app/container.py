from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.subscription import SubscriptionRepository
from app.repositories.subscription_plan import SubscriptionPlanRepository
from app.repositories.subscription_price import SubscriptionPriceRepository
from app.repositories.wallet import WalletRepository

from app.services.subscription import SubscriptionService
from app.services.billing import BillingService


class Container:
    """
    Dependency container.

    Creates repositories and services for one request.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:

        self.db = db

    #
    # Repositories
    #

    @property
    def subscription_repository(
        self,
    ) -> SubscriptionRepository:

        return SubscriptionRepository(
            self.db,
        )

    @property
    def wallet_repository(
        self,
    ) -> WalletRepository:

        return WalletRepository(
            self.db,
        )

    @property
    def subscription_plan_repository(
        self,
    ) -> SubscriptionPlanRepository:

        return SubscriptionPlanRepository(
            self.db,
        )

    @property
    def subscription_price_repository(
        self,
    ) -> SubscriptionPriceRepository:

        return SubscriptionPriceRepository(
            self.db,
        )

    #
    # Services
    #

    @property
    def subscription_service(
        self,
    ) -> SubscriptionService:

        return SubscriptionService(
            db=self.db,
            subscription_repository=self.subscription_repository,
            wallet_repository=self.wallet_repository,
            price_repository=self.subscription_price_repository,
        )

    @property
    def billing_service(
        self,
    ) -> BillingService:

        return BillingService(
            db=self.db,
        )