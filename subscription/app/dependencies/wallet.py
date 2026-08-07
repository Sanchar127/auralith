from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.wallet import WalletService



async def get_wallet_service(
    db: AsyncSession = Depends(get_db),
):

    return WalletService(db)