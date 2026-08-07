from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.schemas.wallet import (
    WalletCreate,
    WalletUpdate,
    WalletResponse,
)

from app.services.wallet import WalletService

from app.dependencies.wallet import (
    get_wallet_service,
)

from app.dependencies.auth import (
    get_current_user,
    require_admin,
)


router = APIRouter(
    prefix="/wallets",
    tags=["Wallets"],
)



# =========================================================
# Create Wallet
# ADMIN ONLY
# =========================================================

@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wallet(

    payload: WalletCreate,

    admin=Depends(
        require_admin
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    return await service.create_wallet(
        payload
    )



# =========================================================
# Get My Wallet
# USER
# =========================================================

@router.get(
    "/me",
    response_model=WalletResponse,
)
async def get_my_wallet(

    current_user=Depends(
        get_current_user
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    wallet = await service.get_wallet(
        current_user.id
    )


    if wallet is None:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )


    return wallet



# =========================================================
# Get Any User Wallet
# ADMIN ONLY
# =========================================================

@router.get(
    "/user/{user_id}",
    response_model=WalletResponse,
)
async def get_user_wallet(

    user_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    wallet = await service.get_wallet(
        user_id
    )


    if wallet is None:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )


    return wallet



# =========================================================
# Update Wallet
# ADMIN ONLY
# =========================================================

@router.patch(
    "/user/{user_id}",
    response_model=WalletResponse,
)
async def update_wallet(

    user_id: UUID,

    payload: WalletUpdate,

    admin=Depends(
        require_admin
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    wallet = await service.update_wallet(
        user_id,
        payload,
    )


    if wallet is None:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )


    return wallet



# =========================================================
# Update Own Wallet Balance
# INTERNAL USE ONLY
# =========================================================

@router.patch(
    "/me",
    response_model=WalletResponse,
)
async def update_my_wallet(

    payload: WalletUpdate,

    current_user=Depends(
        get_current_user
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    wallet = await service.update_wallet(
        current_user.id,
        payload,
    )


    if wallet is None:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )


    return wallet



# =========================================================
# Delete Wallet
# ADMIN ONLY
# =========================================================

@router.delete(
    "/user/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_wallet(

    user_id: UUID,

    admin=Depends(
        require_admin
    ),

    service: WalletService = Depends(
        get_wallet_service
    ),
):

    deleted = await service.delete_wallet(
        user_id
    )


    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )


    return None