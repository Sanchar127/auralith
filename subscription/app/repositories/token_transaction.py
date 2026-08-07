from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.tokentransaction import (
    TokenTransaction
)



class TokenTransactionRepository:


    def __init__(
        self,
        db: AsyncSession
    ):
        self.db=db



    async def create(
        self,
        transaction
    ):

        self.db.add(transaction)

        await self.db.flush()

        return transaction



    async def get_user_transactions(
        self,
        user_id: UUID
    ):

        result = await self.db.execute(
            select(TokenTransaction)
            .where(
                TokenTransaction.user_id==user_id
            )
            .order_by(
                TokenTransaction.created_at.desc()
            )
        )

        return result.scalars().all()



    async def commit(self):

        await self.db.commit()



    async def refresh(
        self,
        obj
    ):
        await self.db.refresh(obj)