from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.tokentransaction import (
    TokenTransaction
)

from app.repositories.token_transaction import (
    TokenTransactionRepository
)

from app.schemas.token_transaction import (
    TokenTransactionCreate
)



class TokenTransactionService:


    def __init__(
        self,
        db: AsyncSession
    ):

        self.repo = TokenTransactionRepository(db)



    async def create(
        self,
        payload: TokenTransactionCreate
    ):


        transaction = TokenTransaction(
            **payload.model_dump()
        )


        await self.repo.create(
            transaction
        )


        await self.repo.commit()


        await self.repo.refresh(
            transaction
        )


        return transaction



    async def list_user_transactions(
        self,
        user_id
    ):

        return await self.repo.get_user_transactions(
            user_id
        )