from __future__ import annotations

import grpc

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.core.logger import logger
from app.grpc.subscription_client import SubscriptionClient


subscription_client = SubscriptionClient()


async def check_token_balance(
    current_user=Depends(get_current_user),
) -> dict[str, str | int]:
    """
    Perform a lightweight pre-flight token check.

    The Subscription service remains the source of truth for
    token balances. This dependency does not reserve or consume
    tokens.

    Actual token reservation and settlement are handled by
    ChatService through the Subscription gRPC service.
    """

    user_id = str(current_user.id)

    logger.info(
        "Checking token balance user_id=%s",
        user_id,
    )

    try:
        subscription = (
            await subscription_client.get_subscription(
                user_id=user_id,
            )
        )

    except grpc.aio.AioRpcError as exc:
        logger.error(
            "Subscription gRPC request failed "
            "user_id=%s code=%s details=%s",
            user_id,
            exc.code(),
            exc.details(),
        )

        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Subscription service unavailable",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify token balance",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected subscription error "
            "user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription service unavailable",
        ) from exc

    if not subscription.active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )

    available_tokens = int(
        subscription.remaining_tokens
    )

    if available_tokens <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Token quota exhausted",
        )

    logger.info(
        "Token balance verified "
        "user_id=%s available_tokens=%s",
        user_id,
        available_tokens,
    )

    return {
        "user_id": user_id,
        "available_tokens": available_tokens,
    }