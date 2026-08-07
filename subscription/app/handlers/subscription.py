from __future__ import annotations

import uuid

import grpc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.subscription import SubscriptionRepository
from app.repositories.wallet import WalletRepository
from app.services.subscription import SubscriptionService

from shared.grpc.generated import (
    subscription_pb2,
    subscription_pb2_grpc,
)


class SubscriptionHandler(
    subscription_pb2_grpc.SubscriptionServiceServicer,
):
    """
    gRPC handler for Subscription Service.

    Responsibilities
    ----------------
    - Parse protobuf requests
    - Call application service
    - Map domain model -> protobuf
    - Convert errors -> gRPC status
    """

    async def _service(
        self,
    ) -> tuple[
        AsyncSession,
        SubscriptionService,
    ]:
        """
        Creates a scoped service for every request.
        """

        session = AsyncSessionLocal()

        subscription_repo = SubscriptionRepository(
            session,
        )

        wallet_repo = WalletRepository(
            session,
        )

        service = SubscriptionService(
            db=session,
            subscription_repository=subscription_repo,
            wallet_repository=wallet_repo,
        )

        return session, service

    async def GetCurrentSubscription(
        self,
        request,
        context,
    ):

        session, service = await self._service()

        try:

            subscription = (
                await service.get_active_subscription(
                    uuid.UUID(request.user_id),
                )
            )

            if subscription is None:

                return (
                    subscription_pb2.SubscriptionResponse(
                        success=False,
                        message="No active subscription",
                    )
                )

            return (
                subscription_pb2.SubscriptionResponse(
                    success=True,
                    message="OK",
                    subscription=self._to_proto(
                        subscription,
                    ),
                )
            )

        finally:

            await session.close()

    async def HasActiveSubscription(
        self,
        request,
        context,
    ):

        session, service = await self._service()

        try:

            subscription = (
                await service.get_active_subscription(
                    uuid.UUID(request.user_id),
                )
            )

            return (
                subscription_pb2.HasActiveSubscriptionResponse(
                    active=subscription is not None,
                )
            )

        finally:

            await session.close()

    async def CreateSubscription(
        self,
        request,
        context,
    ):

        session, service = await self._service()

        try:

            subscription = (
                await service.create_subscription(
                    user_id=uuid.UUID(
                        request.user_id,
                    ),
                    price_id=uuid.UUID(
                        request.price_id,
                    ),
                )
            )

            return (
                subscription_pb2.SubscriptionResponse(
                    success=True,
                    message="Subscription created",
                    subscription=self._to_proto(
                        subscription,
                    ),
                )
            )

        finally:

            await session.close()

    async def CancelSubscription(
        self,
        request,
        context,
    ):

        session, service = await self._service()

        try:

            subscription = (
                await service.cancel_subscription(
                    uuid.UUID(request.user_id),
                )
            )

            if subscription is None:

                return (
                    subscription_pb2.SubscriptionResponse(
                        success=False,
                        message="Subscription not found",
                    )
                )

            return (
                subscription_pb2.SubscriptionResponse(
                    success=True,
                    message="Subscription cancelled",
                    subscription=self._to_proto(
                        subscription,
                    ),
                )
            )

        finally:

            await session.close()

    @staticmethod
    def _to_proto(
        subscription,
    ) -> subscription_pb2.Subscription:

        return subscription_pb2.Subscription(
            id=str(subscription.id),
            user_id=str(subscription.user_id),
            plan_id=str(subscription.plan_id),
            status=subscription.status.value,
            starts_at=subscription.starts_at.isoformat(),
            expires_at=subscription.expires_at.isoformat(),
            auto_renew=subscription.auto_renew,
        )