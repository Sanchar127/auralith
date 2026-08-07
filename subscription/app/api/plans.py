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

from app.dependencies.subscription_plan import (
    get_subscription_plan_service,
)

from app.schemas.plan import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SubscriptionPlanResponse,
)

from app.services.plans import (
    SubscriptionPlanService,
)


router = APIRouter(
    prefix="/plans",
    tags=["Subscription Plans"],
)


# ---------------------------------------------------------
# Create Plan (ADMIN)
# ---------------------------------------------------------

@router.post(
    "",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_plan(
    payload: SubscriptionPlanCreate,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionPlanService = Depends(
        get_subscription_plan_service,
    ),
):

    return await service.create_plan(
        payload
    )



# ---------------------------------------------------------
# List Plans (AUTHENTICATED USER)
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[SubscriptionPlanResponse],
)
async def list_plans(

    skip: int = Query(
        0,
        ge=0,
    ),

    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),

    active_only: bool = Query(
        True
    ),

    user_id=Depends(
        get_current_user
    ),

    service: SubscriptionPlanService = Depends(
        get_subscription_plan_service,
    ),
):

    return await service.list_plans(
        skip=skip,
        limit=limit,
        active_only=active_only,
    )



# ---------------------------------------------------------
# Get Single Plan
# ---------------------------------------------------------

@router.get(
    "/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
async def get_plan(

    plan_id: UUID,

    user_id=Depends(
        get_current_user
    ),

    service: SubscriptionPlanService = Depends(
        get_subscription_plan_service,
    ),
):

    plan = await service.get_plan(
        plan_id
    )


    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Subscription plan not found.",
        )


    return plan



# ---------------------------------------------------------
# Update Plan (ADMIN)
# ---------------------------------------------------------

@router.patch(
    "/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
async def update_plan(

    plan_id: UUID,

    payload: SubscriptionPlanUpdate,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionPlanService = Depends(
        get_subscription_plan_service,
    ),
):

    plan = await service.update_plan(
        plan_id,
        payload,
    )


    if plan is None:
        raise HTTPException(
            status_code=404,
            detail="Subscription plan not found.",
        )


    return plan



# ---------------------------------------------------------
# Delete Plan (ADMIN)
# ---------------------------------------------------------

@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_plan(

    plan_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: SubscriptionPlanService = Depends(
        get_subscription_plan_service,
    ),
):

    deleted = await service.delete_plan(
        plan_id
    )


    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Subscription plan not found.",
        )


    return None