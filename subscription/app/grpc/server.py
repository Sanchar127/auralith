from __future__ import annotations

import asyncio

import grpc

from generated import subscription_pb2
from generated import subscription_pb2_grpc

from app.core.logger import logger
from app.db.session import AsyncSessionLocal
from app.services.token import TokenService


class SubscriptionGrpcService(
    subscription_pb2_grpc.SubscriptionServiceServicer,
):
    """
    gRPC adapter for the Subscription service.

    The gRPC layer is intentionally thin.

    Business logic is handled by TokenService.
    Database operations are handled by TokenService.
    """

    # ============================================================
    # GET SUBSCRIPTION
    # ============================================================

    async def GetSubscription(
        self,
        request: subscription_pb2.GetSubscriptionRequest,
        context: grpc.aio.ServicerContext,
    ) -> subscription_pb2.SubscriptionResponse:

        user_id = request.user_id.strip()

        if not user_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "user_id is required",
            )

        logger.info(
            "gRPC GetSubscription request",
            extra={
                "user_id": user_id,
            },
        )

        try:
            async with AsyncSessionLocal() as db:

                service = TokenService(db)

                result = await service.get_subscription(
                    user_id=user_id,
                )

                return subscription_pb2.SubscriptionResponse(
                    active=result.active,
                    remaining_tokens=result.remaining_tokens,
                )

        except ValueError as exc:

            logger.warning(
                "GetSubscription rejected",
                extra={
                    "user_id": user_id,
                    "reason": str(exc),
                },
            )

            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                str(exc),
            )

        except Exception:

            logger.exception(
                "GetSubscription failed",
                extra={
                    "user_id": user_id,
                },
            )

            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Internal server error",
            )

    # ============================================================
    # RESERVE TOKENS
    # ============================================================

    async def ReserveTokens(
        self,
        request: subscription_pb2.ReserveTokensRequest,
        context: grpc.aio.ServicerContext,
    ) -> subscription_pb2.ReserveTokensResponse:

        user_id = request.user_id.strip()
        request_id = request.request_id.strip()
        model = request.model.strip()

        if not user_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "user_id is required",
            )

        if not request_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "request_id is required",
            )

        if request.estimated_tokens <= 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "estimated_tokens must be greater than zero",
            )

        logger.info(
            "gRPC ReserveTokens request",
            extra={
                "user_id": user_id,
                "request_id": request_id,
                "estimated_tokens": request.estimated_tokens,
                "model": model,
            },
        )

        try:
            async with AsyncSessionLocal() as db:

                service = TokenService(db)

                result = await service.reserve_tokens(
                    user_id=user_id,
                    estimated_tokens=request.estimated_tokens,
                    request_id=request_id,
                    model=model,
                )

                logger.info(
                    "Tokens reserved",
                    extra={
                        "user_id": user_id,
                        "request_id": request_id,
                        "reservation_id": result.reservation_id,
                        "reserved_tokens": result.reserved_tokens,
                        "remaining_tokens": result.remaining_tokens,
                    },
                )

                return subscription_pb2.ReserveTokensResponse(
                    success=result.success,
                    reservation_id=result.reservation_id,
                    reserved_tokens=result.reserved_tokens,
                    remaining_tokens=result.remaining_tokens,
                    message=result.message,
                )

        except ValueError as exc:

            logger.warning(
                "Token reservation rejected",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "reason": str(exc),
                },
            )

            return subscription_pb2.ReserveTokensResponse(
                success=False,
                reservation_id="",
                reserved_tokens=0,
                remaining_tokens=0,
                message=str(exc),
            )

        except Exception:

            logger.exception(
                "ReserveTokens failed",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                },
            )

            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Internal server error",
            )

    # ============================================================
    # SETTLE TOKENS
    # ============================================================

    async def SettleTokens(
        self,
        request: subscription_pb2.SettleTokensRequest,
        context: grpc.aio.ServicerContext,
    ) -> subscription_pb2.SettleTokensResponse:

        user_id = request.user_id.strip()
        reservation_id = request.reservation_id.strip()
        request_id = request.request_id.strip()
        model = request.model.strip()

        if not user_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "user_id is required",
            )

        if not reservation_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "reservation_id is required",
            )

        if not request_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "request_id is required",
            )

        if request.input_tokens < 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "input_tokens cannot be negative",
            )

        if request.output_tokens < 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "output_tokens cannot be negative",
            )

        if request.total_tokens < 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "total_tokens cannot be negative",
            )

        if (
            request.total_tokens
            != request.input_tokens + request.output_tokens
        ):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "total_tokens must equal input_tokens + output_tokens",
            )

        logger.info(
            "gRPC SettleTokens request",
            extra={
                "user_id": user_id,
                "reservation_id": reservation_id,
                "request_id": request_id,
                "input_tokens": request.input_tokens,
                "output_tokens": request.output_tokens,
                "total_tokens": request.total_tokens,
                "model": model,
            },
        )

        try:
            async with AsyncSessionLocal() as db:

                service = TokenService(db)

                result = await service.settle_tokens(
                    user_id=user_id,
                    reservation_id=reservation_id,
                    request_id=request_id,
                    input_tokens=request.input_tokens,
                    output_tokens=request.output_tokens,
                    total_tokens=request.total_tokens,
                    model=model,
                )

                logger.info(
                    "Tokens settled",
                    extra={
                        "user_id": user_id,
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                        "charged_tokens": result.charged_tokens,
                        "refunded_tokens": result.refunded_tokens,
                        "remaining_tokens": result.remaining_tokens,
                    },
                )

                return subscription_pb2.SettleTokensResponse(
                    success=result.success,
                    charged_tokens=result.charged_tokens,
                    refunded_tokens=result.refunded_tokens,
                    remaining_tokens=result.remaining_tokens,
                    message=result.message,
                )

        except ValueError as exc:

            logger.warning(
                "Token settlement rejected",
                extra={
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "request_id": request_id,
                    "reason": str(exc),
                },
            )

            return subscription_pb2.SettleTokensResponse(
                success=False,
                charged_tokens=0,
                refunded_tokens=0,
                remaining_tokens=0,
                message=str(exc),
            )

        except Exception:

            logger.exception(
                "SettleTokens failed",
                extra={
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "request_id": request_id,
                },
            )

            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Internal server error",
            )

    # ============================================================
    # RELEASE TOKENS
    # ============================================================

    async def ReleaseTokens(
        self,
        request: subscription_pb2.ReleaseTokensRequest,
        context: grpc.aio.ServicerContext,
    ) -> subscription_pb2.ReleaseTokensResponse:

        user_id = request.user_id.strip()
        reservation_id = request.reservation_id.strip()
        request_id = request.request_id.strip()

        if not user_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "user_id is required",
            )

        if not reservation_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "reservation_id is required",
            )

        if not request_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "request_id is required",
            )

        logger.info(
            "gRPC ReleaseTokens request",
            extra={
                "user_id": user_id,
                "reservation_id": reservation_id,
                "request_id": request_id,
            },
        )

        try:
            async with AsyncSessionLocal() as db:

                service = TokenService(db)

                result = await service.release_tokens(
                    user_id=user_id,
                    reservation_id=reservation_id,
                    request_id=request_id,
                )

                logger.info(
                    "Tokens released",
                    extra={
                        "user_id": user_id,
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                        "released_tokens": result.released_tokens,
                        "remaining_tokens": result.remaining_tokens,
                    },
                )

                return subscription_pb2.ReleaseTokensResponse(
                    success=result.success,
                    released_tokens=result.released_tokens,
                    remaining_tokens=result.remaining_tokens,
                    message=result.message,
                )

        except ValueError as exc:

            logger.warning(
                "Token release rejected",
                extra={
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "request_id": request_id,
                    "reason": str(exc),
                },
            )

            return subscription_pb2.ReleaseTokensResponse(
                success=False,
                released_tokens=0,
                remaining_tokens=0,
                message=str(exc),
            )

        except Exception:

            logger.exception(
                "ReleaseTokens failed",
                extra={
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "request_id": request_id,
                },
            )

            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Internal server error",
            )


# ================================================================
# SERVER
# ================================================================


async def serve() -> None:
    """
    Start the Subscription gRPC server.
    """

    address = "[::]:50052"

    logger.info(
        "Starting Subscription gRPC server",
        extra={
            "address": address,
        },
    )

    server = grpc.aio.server(
        options=[
            (
                "grpc.max_receive_message_length",
                10 * 1024 * 1024,
            ),
            (
                "grpc.max_send_message_length",
                10 * 1024 * 1024,
            ),
        ]
    )

    subscription_pb2_grpc.add_SubscriptionServiceServicer_to_server(
        SubscriptionGrpcService(),
        server,
    )

    server.add_insecure_port(address)

    await server.start()

    logger.info(
        "Subscription gRPC server started",
        extra={
            "address": address,
        },
    )

    try:
        await server.wait_for_termination()

    except asyncio.CancelledError:

        logger.info(
            "Subscription gRPC server shutdown requested",
        )

        await server.stop(
            grace=5,
        )

        logger.info(
            "Subscription gRPC server stopped",
        )

    except Exception:

        logger.exception(
            "Subscription gRPC server terminated unexpectedly",
        )

        await server.stop(
            grace=5,
        )

        raise