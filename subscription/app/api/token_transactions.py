from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.schemas.token_transaction import (
    TokenTransactionCreate,
    TokenTransactionResponse,
)

from app.services.token_transaction import (
    TokenTransactionService,
)

from app.dependencies.token_transaction import (
    get_token_transaction_service,
)

from app.dependencies.auth import (
    get_current_user,
    require_admin,
)


router = APIRouter(
    prefix="/token-transactions",
    tags=["Token Transactions"],
)



# =========================================================
# Create Token Transaction
# USER + ADMIN
# =========================================================

@router.post(
    "",
    response_model=TokenTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(

    payload: TokenTransactionCreate,

    current_user=Depends(
        get_current_user
    ),

    service: TokenTransactionService = Depends(
        get_token_transaction_service
    ),
):

    # overwrite user_id from auth
    payload.user_id = current_user.id


    return await service.create(
        payload
    )



# =========================================================
# My Transaction History
# USER
# =========================================================

@router.get(
    "/me",
    response_model=list[TokenTransactionResponse],
)
async def get_my_transactions(

    current_user=Depends(
        get_current_user
    ),

    service: TokenTransactionService = Depends(
        get_token_transaction_service
    ),
):

    return await service.list_user_transactions(
        current_user.id
    )



# =========================================================
# User Transaction History
# ADMIN ONLY
# =========================================================

@router.get(
    "/user/{user_id}",
    response_model=list[TokenTransactionResponse],
)
async def get_user_transactions(

    user_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: TokenTransactionService = Depends(
        get_token_transaction_service
    ),
):

    return await service.list_user_transactions(
        user_id
    )



# =========================================================
# Get Single Transaction
# USER OWN / ADMIN
# =========================================================

@router.get(
    "/{transaction_id}",
    response_model=TokenTransactionResponse,
)
async def get_transaction(

    transaction_id: UUID,

    current_user=Depends(
        get_current_user
    ),

    service: TokenTransactionService = Depends(
        get_token_transaction_service
    ),
):

    transaction = await service.get(
        transaction_id
    )


    if transaction is None:

        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )


    # security check
    if (
        transaction.user_id != current_user.id
        and current_user.role != "admin"
    ):

        raise HTTPException(
            status_code=403,
            detail="Not allowed",
        )


    return transaction