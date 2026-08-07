from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.token_wallet import TokenWallet


class WalletRepository:
    """
    Repository for token wallet operations.
    """

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


    async def get_by_user(
        self,
        user_id: UUID,
    ) -> TokenWallet | None:

        result = await self.db.execute(
            select(TokenWallet)
            .where(
                TokenWallet.user_id == user_id
            )
        )

        return result.scalar_one_or_none()



    async def get_by_user_for_update(
        self,
        user_id: UUID,
    ) -> TokenWallet | None:
        """
        Lock wallet row during token deduction.

        Prevents race conditions when
        multiple requests consume tokens
        at the same time.
        """

        result = await self.db.execute(
            select(TokenWallet)
            .where(
                TokenWallet.user_id == user_id
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()



    async def create(
        self,
        wallet: TokenWallet,
    ) -> TokenWallet:

        self.db.add(wallet)

        await self.db.flush()

        return wallet



    async def update(
        self,
        wallet: TokenWallet,
    ) -> TokenWallet:

        await self.db.flush()

        return wallet



    async def delete(
        self,
        wallet: TokenWallet,
    ):

        await self.db.delete(wallet)



    async def commit(
        self,
    ):

        await self.db.commit()



    async def refresh(
        self,
        obj,
    ):

        await self.db.refresh(obj)