import logging
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


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallets",
    tags=["Wallets"],
)


# =========================================================
# Create Wallet
# USER (Creates wallet for themselves)
# =========================================================

@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wallet(
    payload: WalletCreate,  # Only has initial_tokens
    current_user=Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Create a wallet for the authenticated user.
    """
    logger.info("=" * 50)
    logger.info("CREATE WALLET ENDPOINT CALLED")
    
    try:
        # Get user_id from JWT token
        user_id = UUID(current_user["id"])
        logger.info(f"User ID from JWT: {user_id}")
        
        # Create wallet data as dict (user_id comes from JWT, not from request)
        wallet_data = {
            "user_id": user_id,
            "initial_tokens": payload.initial_tokens
        }
        
        logger.info(f"Creating wallet for user: {user_id} with {payload.initial_tokens} tokens")
        result = await service.create_wallet(wallet_data)
        
        logger.info(f"✅ Created wallet: {result}")
        logger.info("=" * 50)
        return result
        
    except KeyError:
        logger.error("No 'id' field found in current_user")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token - missing user ID"
        )
    except ValueError as e:
        logger.error(f"Invalid UUID format: {current_user.get('id')}")
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create wallet: {str(e)}"
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
    current_user=Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Get the authenticated user's wallet.
    """
    logger.info("=" * 50)
    logger.info("GET MY WALLET ENDPOINT CALLED")
    
    try:
        user_id = UUID(current_user["id"])
        logger.info(f"Looking for wallet for user: {user_id}")
        
        wallet = await service.get_wallet(user_id)

        if wallet is None:
            logger.warning(f"⚠️ No wallet found for user_id: {user_id}")
            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        logger.info(f"✅ Wallet found: {wallet}")
        logger.info("=" * 50)
        return wallet
        
    except KeyError:
        logger.error("No 'id' field found in current_user")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token - missing user ID"
        )
    except ValueError as e:
        logger.error(f"Invalid UUID format: {current_user.get('id')}")
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )


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
    admin=Depends(require_admin),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Get any user's wallet (admin only).
    """
    logger.info(f"Admin getting wallet for user_id: {user_id}")
    wallet = await service.get_wallet(user_id)

    if wallet is None:
        logger.warning(f"No wallet found for user_id: {user_id}")
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
    admin=Depends(require_admin),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Update any user's wallet (admin only).
    """
    logger.info(f"Admin updating wallet for user_id: {user_id}")
    wallet = await service.update_wallet(user_id, payload)

    if wallet is None:
        logger.warning(f"No wallet found for user_id: {user_id}")
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return wallet


# =========================================================
# Update Own Wallet Balance
# USER (Updates their own wallet)
# =========================================================

@router.patch(
    "/me",
    response_model=WalletResponse,
)
async def update_my_wallet(
    payload: WalletUpdate,
    current_user=Depends(get_current_user),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Update the authenticated user's wallet.
    """
    logger.info("=" * 50)
    logger.info("UPDATE MY WALLET ENDPOINT CALLED")
    
    try:
        user_id = UUID(current_user["id"])
        logger.info(f"Updating wallet for user: {user_id}")
        
        wallet = await service.update_wallet(user_id, payload)

        if wallet is None:
            logger.warning(f"No wallet found for user_id: {user_id}")
            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        logger.info(f"✅ Wallet updated: {wallet}")
        logger.info("=" * 50)
        return wallet
        
    except KeyError:
        logger.error("No 'id' field found in current_user")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token - missing user ID"
        )
    except ValueError as e:
        logger.error(f"Invalid UUID format: {current_user.get('id')}")
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format"
        )


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
    admin=Depends(require_admin),
    service: WalletService = Depends(get_wallet_service),
):
    """
    Delete any user's wallet (admin only).
    """
    logger.info(f"Admin deleting wallet for user_id: {user_id}")
    deleted = await service.delete_wallet(user_id)

    if not deleted:
        logger.warning(f"No wallet found for user_id: {user_id}")
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return None