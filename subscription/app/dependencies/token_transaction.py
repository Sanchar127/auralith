from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

from app.services.token_transaction import (
    TokenTransactionService,
)



async def get_token_transaction_service(
    db: AsyncSession = Depends(get_db),
):

    return TokenTransactionService(db)