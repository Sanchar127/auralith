from __future__ import annotations

import grpc

from app.core.logger import logger
from generated import subscription_pb2
from generated import subscription_pb2_grpc


class SubscriptionClient:
    """
    Async gRPC client for the Subscription microservice.

    The Subscription service owns:
        - subscriptions
        - token wallets
        - token reservations
        - token transactions
        - token balance

    The Chat service only requests operations through this client.
    """

    def __init__(
        self,
        address: str = "subscription:50052",
    ) -> None:
        self.address = address

        self.channel = grpc.aio.insecure_channel(
            self.address,
            options=[
                (
                    "grpc.keepalive_time_ms",
                    30_000,
                ),
                (
                    "grpc.keepalive_timeout_ms",
                    10_000,
                ),
                (
                    "grpc.keepalive_permit_without_calls",
                    1,
                ),
                (
                    "grpc.http2.max_pings_without_data",
                    0,
                ),
            ],
        )

        self.stub = (
            subscription_pb2_grpc.SubscriptionServiceStub(
                self.channel
            )
        )

        logger.info(
            "Subscription gRPC client initialized: %s",
            self.address,
        )

    async def get_subscription(
        self,
        user_id: str,
    ):
        """
        Get the user's current subscription and token balance.
        """

        if not user_id:
            raise ValueError(
                "user_id cannot be empty"
            )

        request = (
            subscription_pb2.GetSubscriptionRequest(
                user_id=user_id,
            )
        )

        try:
            return await self.stub.GetSubscription(
                request,
                timeout=3.0,
            )

        except grpc.aio.AioRpcError as exc:
            logger.error(
                "GetSubscription failed "
                "user_id=%s code=%s details=%s",
                user_id,
                exc.code(),
                exc.details(),
            )
            raise

    async def reserve_tokens(
        self,
        *,
        user_id: str,
        estimated_tokens: int,
        request_id: str,
        model: str,
    ):
        """
        Reserve tokens before executing the LLM request.

        The Subscription service decides whether
        the user has enough available tokens.
        """

        if not user_id:
            raise ValueError(
                "user_id cannot be empty"
            )

        if estimated_tokens <= 0:
            raise ValueError(
                "estimated_tokens must be greater than zero"
            )

        if not request_id:
            raise ValueError(
                "request_id cannot be empty"
            )

        request = (
            subscription_pb2.ReserveTokensRequest(
                user_id=user_id,
                estimated_tokens=estimated_tokens,
                request_id=request_id,
                model=model,
            )
        )

        try:
            return await self.stub.ReserveTokens(
                request,
                timeout=3.0,
            )

        except grpc.aio.AioRpcError as exc:
            logger.error(
                "ReserveTokens failed "
                "user_id=%s request_id=%s "
                "code=%s details=%s",
                user_id,
                request_id,
                exc.code(),
                exc.details(),
            )
            raise

    async def settle_tokens(
        self,
        *,
        user_id: str,
        reservation_id: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model: str,
    ):
        """
        Settle the token reservation using
        the actual LLM token usage.
        """

        if not user_id:
            raise ValueError(
                "user_id cannot be empty"
            )

        if not reservation_id:
            raise ValueError(
                "reservation_id cannot be empty"
            )

        if not request_id:
            raise ValueError(
                "request_id cannot be empty"
            )

        if input_tokens < 0:
            raise ValueError(
                "input_tokens cannot be negative"
            )

        if output_tokens < 0:
            raise ValueError(
                "output_tokens cannot be negative"
            )

        if total_tokens < 0:
            raise ValueError(
                "total_tokens cannot be negative"
            )

        request = (
            subscription_pb2.SettleTokensRequest(
                user_id=user_id,
                reservation_id=reservation_id,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                model=model,
            )
        )

        try:
            return await self.stub.SettleTokens(
                request,
                timeout=3.0,
            )

        except grpc.aio.AioRpcError as exc:
            logger.error(
                "SettleTokens failed "
                "user_id=%s reservation_id=%s "
                "request_id=%s code=%s details=%s",
                user_id,
                reservation_id,
                request_id,
                exc.code(),
                exc.details(),
            )
            raise

    async def release_tokens(
        self,
        *,
        user_id: str,
        reservation_id: str,
        request_id: str,
    ):
        """
        Release a token reservation when the LLM
        request fails before settlement.
        """

        if not user_id:
            raise ValueError(
                "user_id cannot be empty"
            )

        if not reservation_id:
            raise ValueError(
                "reservation_id cannot be empty"
            )

        if not request_id:
            raise ValueError(
                "request_id cannot be empty"
            )

        request = (
            subscription_pb2.ReleaseTokensRequest(
                user_id=user_id,
                reservation_id=reservation_id,
                request_id=request_id,
            )
        )

        try:
            return await self.stub.ReleaseTokens(
                request,
                timeout=3.0,
            )

        except grpc.aio.AioRpcError as exc:
            logger.error(
                "ReleaseTokens failed "
                "user_id=%s reservation_id=%s "
                "request_id=%s code=%s details=%s",
                user_id,
                reservation_id,
                request_id,
                exc.code(),
                exc.details(),
            )
            raise

    async def close(self) -> None:
        """
        Close the gRPC channel gracefully.
        """

        await self.channel.close()

        logger.info(
            "Subscription gRPC client closed"
        )