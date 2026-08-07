from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.dependencies.auth import (
    get_current_user,
    require_admin,
)

from app.dependencies.subscription import (
    get_subscription_service,
)

from app.exceptions import (
    SubscriptionAlreadyActiveError,
    SubscriptionNotFoundError,
)

from app.schemas.subscription import (
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionUpdate,
)

from app.services.subscriptions import (
    SubscriptionService,
)


router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)



# =========================================================
# Create Subscription
# USER
# =========================================================

@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(

    payload: SubscribeRequest,

    current_user=Depends(
        get_current_user
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    try:

        return await service.create_subscription(

            user_id=current_user.id,

            price_id=payload.price_id,
        )


    except SubscriptionAlreadyActiveError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


    except SubscriptionNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )



# =========================================================
# List All Subscriptions
# ADMIN ONLY
# =========================================================

@router.get(
    "",
    response_model=list[SubscriptionResponse],
)
async def list_subscriptions(

    skip: int = Query(
        0,
        ge=0,
    ),

    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),

    admin=Depends(
        require_admin
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    return await service.list_subscriptions(
        skip=skip,
        limit=limit,
    )



# =========================================================
# Get Subscription By ID
# ADMIN
# =========================================================

@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
)
async def get_subscription(

    subscription_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    subscription = await service.get_subscription(
        subscription_id
    )


    if subscription is None:

        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )


    return subscription



# =========================================================
# Get Current User Subscription
# USER
# =========================================================

@router.get(
    "/me",
    response_model=SubscriptionResponse,
)
async def get_my_subscription(

    current_user=Depends(
        get_current_user
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    subscription = await service.get_active_subscription(
        current_user.id
    )


    if subscription is None:

        raise HTTPException(
            status_code=404,
            detail="Active subscription not found.",
        )


    return subscription



# =========================================================
# Get User Subscription
# ADMIN
# =========================================================

@router.get(
    "/user/{user_id}",
    response_model=SubscriptionResponse,
)
async def get_user_subscription(

    user_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    subscription = await service.get_active_subscription(
        user_id
    )


    if subscription is None:

        raise HTTPException(
            status_code=404,
            detail="Active subscription not found.",
        )


    return subscription



# =========================================================
# Update Subscription
# ADMIN ONLY
# =========================================================

@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
)
async def update_subscription(

    subscription_id: UUID,

    payload: SubscriptionUpdate,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    subscription = await service.update_subscription(
        subscription_id,
        payload,
    )


    if subscription is None:

        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )


    return subscription



# =========================================================
# Cancel Subscription
# USER / ADMIN
# =========================================================

@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
)
async def cancel_subscription(

    subscription_id: UUID,

    current_user=Depends(
        get_current_user
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    subscription = await service.cancel_subscription(
        subscription_id
    )


    if subscription is None:

        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )


    return subscription



# =========================================================
# Delete Subscription
# ADMIN ONLY
# =========================================================

@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_subscription(

    subscription_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionService = Depends(
        get_subscription_service
    ),
):

    deleted = await service.delete_subscription(
        subscription_id
    )


    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )


    return None