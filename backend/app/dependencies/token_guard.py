from fastapi import (
    Depends,
    HTTPException,
    status,
)

from app.core.dependencies import (
    get_current_user,
)

from app.grpc.subscription_client import (
    SubscriptionClient,
)


subscription_client = SubscriptionClient()



async def check_token_balance(
    current_user=Depends(
        get_current_user
    ),
):

    user_id = current_user["id"]


    try:

        wallet = await subscription_client.get_wallet(
            user_id=user_id,
        )


    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Subscription service unavailable",
        ) from exc



    if wallet is None:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token wallet not found",
        )



    available_tokens = (
        wallet["available_tokens"]
    )


    if available_tokens <= 0:

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Token quota exhausted",
        )



    return {
        "user_id": user_id,
        "available_tokens": available_tokens,
    }