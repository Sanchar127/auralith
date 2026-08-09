from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.token_wallet import TokenWallet

from app.db.model.tokentransaction import (
    TokenTransaction,
    TokenTransactionType,
)

from app.repositories.wallet import (
    WalletRepository,
)

from app.schemas.wallet import (
    WalletCreate,
    WalletUpdate,
)



class WalletService:
    """
    Handles wallet CRUD and token accounting.
    """

    def __init__(
        self,
        db: AsyncSession,
    ):

        self.repo = WalletRepository(db)

        self.db = db



    # =====================================================
    # CRUD
    # =====================================================

    async def get_wallet(
        self,
        user_id: UUID,
    ):

        return await self.repo.get_by_user(
            user_id
        )



    async def create_wallet(
        self,
        wallet_data: dict,  # Changed from payload: WalletCreate to dict
    ):
        """
        Create a wallet for a user.
        
        Args:
            wallet_data: Dict with 'user_id' and 'initial_tokens'
        """
        # Extract data from dict
        user_id = wallet_data.get("user_id")
        initial_tokens = wallet_data.get("initial_tokens", 0)

        existing = await self.repo.get_by_user(
            user_id
        )


        if existing:
            return existing



        wallet = TokenWallet(
            user_id=user_id,
            available_tokens=initial_tokens,
            lifetime_used_tokens=0,
        )


        await self.repo.create(
            wallet
        )

        await self.repo.commit()

        await self.repo.refresh(
            wallet
        )


        return wallet



    async def update_wallet(
        self,
        user_id: UUID,
        payload: WalletUpdate,
    ):

        wallet = await self.repo.get_by_user(
            user_id
        )


        if wallet is None:
            return None



        values = payload.model_dump(
            exclude_unset=True
        )


        for key, value in values.items():

            setattr(
                wallet,
                key,
                value,
            )


        await self.repo.commit()

        await self.repo.refresh(
            wallet
        )


        return wallet



    async def delete_wallet(
        self,
        user_id: UUID,
    ):

        wallet = await self.repo.get_by_user(
            user_id
        )


        if wallet is None:
            return False



        await self.repo.delete(
            wallet
        )

        await self.repo.commit()


        return True



    # =====================================================
    # TOKEN MANAGEMENT
    # =====================================================


    async def check_balance(
        self,
        user_id: UUID,
        required_tokens: int,
    ) -> bool:
        """
        Check if user has enough tokens.
        Called before LLM execution.
        """


        wallet = await self.repo.get_by_user(
            user_id
        )


        if wallet is None:
            return False



        return (
            wallet.available_tokens
            >= required_tokens
        )



    async def consume_tokens(
        self,
        user_id: UUID,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ):
        """
        Deduct tokens after LLM completion.

        Creates immutable token transaction history.
        """


        total_tokens = (
            input_tokens +
            output_tokens
        )



        wallet = await self.repo.get_by_user_for_update(
            user_id
        )


        if wallet is None:

            raise Exception(
                "Wallet not found"
            )



        if wallet.available_tokens < total_tokens:

            raise Exception(
                "Insufficient token balance"
            )



        balance_before = (
            wallet.available_tokens
        )


        wallet.available_tokens -= (
            total_tokens
        )


        wallet.lifetime_used_tokens += (
            total_tokens
        )



        transaction = TokenTransaction(
            user_id=user_id,

            type=TokenTransactionType.CHAT,

            model=model,

            input_tokens=input_tokens,

            output_tokens=output_tokens,

            total_tokens=total_tokens,

            balance_before=balance_before,

            balance_after=wallet.available_tokens,
        )



        self.db.add(
            transaction
        )


        await self.repo.commit()


        await self.repo.refresh(
            wallet
        )


        return wallet