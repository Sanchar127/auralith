from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger

from app.db.model.token_reservation import (
    TokenReservation,
    TokenReservationStatus,
)

from app.db.model.tokentransaction import (
    TokenTransaction,
    TokenTransactionType,
)

from app.db.model.token_wallet import TokenWallet


# ============================================================
# RESULT OBJECTS
# ============================================================


@dataclass(slots=True)
class SubscriptionResult:
    active: bool
    remaining_tokens: int


@dataclass(slots=True)
class ReserveResult:
    success: bool
    reservation_id: str
    reserved_tokens: int
    remaining_tokens: int
    message: str


@dataclass(slots=True)
class SettleResult:
    success: bool
    charged_tokens: int
    refunded_tokens: int
    remaining_tokens: int
    message: str


@dataclass(slots=True)
class ReleaseResult:
    success: bool
    released_tokens: int
    remaining_tokens: int
    message: str


# ============================================================
# TOKEN SERVICE
# ============================================================


class TokenService:
    """
    Business logic for token accounting.

    Responsibilities:

    - Get subscription/token balance
    - Reserve tokens before an AI request
    - Settle reservation using actual usage
    - Release reservation when AI fails
    - Prevent double charging
    - Protect wallet with database row locks
    - Maintain token transaction history

    This service is the ONLY layer that should mutate
    TokenWallet balances.
    """

    # How long a reservation is valid.
    #
    # This protects the system from abandoned reservations.
    RESERVATION_TTL_MINUTES = 10

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        self.db = db

    # ========================================================
    # GET SUBSCRIPTION / BALANCE
    # ========================================================

    async def get_subscription(
        self,
        *,
        user_id: str,
    ) -> SubscriptionResult:
        """
        Get user's current token balance.

        This operation does not modify the wallet.
        """

        user_id = self._validate_user_id(user_id)

        wallet = await self._get_wallet(
            user_id=user_id,
            lock=False,
        )

        if wallet is None:
            return SubscriptionResult(
                active=False,
                remaining_tokens=0,
            )

        return SubscriptionResult(
            active=wallet.available_tokens > 0,
            remaining_tokens=int(
                wallet.available_tokens
            ),
        )

    # ========================================================
    # RESERVE TOKENS
    # ========================================================

    async def reserve_tokens(
        self,
        *,
        user_id: str,
        estimated_tokens: int,
        request_id: str,
        model: str,
    ) -> ReserveResult:
        """
        Reserve tokens before executing the LLM request.

        Example:

            wallet = 10,000

            reserve 4,000

            wallet = 6,000
            reservation = 4,000

        The wallet row is locked with SELECT FOR UPDATE
        so concurrent requests cannot spend the same tokens.

        request_id provides idempotency.
        """

        user_id = self._validate_user_id(user_id)
        request_id = self._validate_request_id(
            request_id
        )

        model = (model or "").strip()

        if estimated_tokens <= 0:
            raise ValueError(
                "estimated_tokens must be greater than zero"
            )

        # ----------------------------------------------------
        # Check whether this request was already processed.
        # ----------------------------------------------------

        existing = await self._get_reservation_by_request_id(
            user_id=user_id,
            request_id=request_id,
        )

        if existing is not None:

            logger.info(
                "Returning existing token reservation",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "reservation_id": str(existing.id),
                },
            )

            if (
                existing.status
                == TokenReservationStatus.PENDING
            ):
                wallet = await self._get_wallet(
                    user_id=user_id,
                    lock=False,
                )

                return ReserveResult(
                    success=True,
                    reservation_id=str(existing.id),
                    reserved_tokens=int(
                        existing.reserved_tokens
                    ),
                    remaining_tokens=(
                        int(wallet.available_tokens)
                        if wallet
                        else 0
                    ),
                    message="Existing reservation returned",
                )

            if (
                existing.status
                == TokenReservationStatus.SETTLED
            ):
                return ReserveResult(
                    success=False,
                    reservation_id=str(existing.id),
                    reserved_tokens=int(
                        existing.reserved_tokens
                    ),
                    remaining_tokens=0,
                    message=(
                        "Request has already been settled"
                    ),
                )

            if (
                existing.status
                == TokenReservationStatus.RELEASED
            ):
                return ReserveResult(
                    success=False,
                    reservation_id=str(existing.id),
                    reserved_tokens=0,
                    remaining_tokens=0,
                    message=(
                        "Request has already been released"
                    ),
                )

        # ----------------------------------------------------
        # Begin transaction.
        #
        # We explicitly lock the wallet row.
        # ----------------------------------------------------

        try:

            wallet = await self._get_wallet(
                user_id=user_id,
                lock=True,
            )

            if wallet is None:
                raise ValueError(
                    "Token wallet not found"
                )

            available_tokens = int(
                wallet.available_tokens
            )

            # ------------------------------------------------
            # Check balance.
            # ------------------------------------------------

            logger.info(
                "Checking token reservation balance",
                extra={
                    "user_id": user_id,
                    "available_tokens": available_tokens,
                    "estimated_tokens": estimated_tokens,
                    "request_id": request_id,
                    "model": model,
                },
            )

            if available_tokens < estimated_tokens:
                raise ValueError(
                    f"Insufficient token balance: "
                    f"available={available_tokens}, "
                    f"estimated={estimated_tokens}"
                )
            # ------------------------------------------------
            # Deduct from available balance.
            # ------------------------------------------------

            wallet.available_tokens = (
                available_tokens
                - estimated_tokens
            )

            # ------------------------------------------------
            # Create reservation.
            # ------------------------------------------------

            reservation_id = uuid4()

            now = datetime.now(timezone.utc)

            expires_at = (
                now
                + timedelta(
                    minutes=self.RESERVATION_TTL_MINUTES
                )
            )

            reservation = TokenReservation(
                id=reservation_id,
                user_id=user_id,
                request_id=request_id,
                reserved_tokens=estimated_tokens,
                status=TokenReservationStatus.PENDING,
                model=model,
                created_at=now,
                expires_at=expires_at,
            )

            self.db.add(reservation)

            # ------------------------------------------------
            # Create audit transaction.
            # ------------------------------------------------

            transaction = TokenTransaction(
            id=uuid4(),
            user_id=user_id,
            reservation_id=reservation_id,
            request_id=request_id,
            type=TokenTransactionType.RESERVATION,
            input_tokens=0,
            output_tokens=0,
            total_tokens=estimated_tokens,
            balance_before=available_tokens,
            balance_after=int(wallet.available_tokens),
            model=model,
            created_at=now,
        )
            self.db.add(transaction)

            await self.db.commit()

            logger.info(
                "Tokens reserved successfully",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "reservation_id": str(
                        reservation_id
                    ),
                    "reserved_tokens": estimated_tokens,
                    "remaining_tokens": (
                        wallet.available_tokens
                    ),
                },
            )

            return ReserveResult(
                success=True,
                reservation_id=str(
                    reservation_id
                ),
                reserved_tokens=estimated_tokens,
                remaining_tokens=int(
                    wallet.available_tokens
                ),
                message="Tokens reserved successfully",
            )

        except Exception:

            await self.db.rollback()

            logger.exception(
                "Token reservation failed",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "estimated_tokens": estimated_tokens,
                },
            )

            raise

    # ========================================================
    # SETTLE TOKENS
    # ========================================================

   
    async def settle_tokens(
        self,
        *,
        user_id: str,
        reservation_id: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model: str,
        ) -> SettleResult:
            """
            Settle a pending token reservation using actual token usage.

            Reservation flow:

                Reserve:
                    wallet.available_tokens -= reserved_tokens

                Settlement:
                    actual_tokens = input_tokens + output_tokens
                    refund = reserved_tokens - actual_tokens

                    wallet.available_tokens += refund
                    wallet.lifetime_used_tokens += actual_tokens

            Example:

                Reserved: 5,000
                Actual:   2,500
                Refund:   2,500

                Wallet:
                    reserved amount already deducted
                    2,500 unused tokens returned
                    2,500 tokens counted as used
            """

            # ============================================================
            # VALIDATE INPUT
            # ============================================================

            user_id = self._validate_user_id(user_id)

            request_id = self._validate_request_id(
                request_id
            )

            reservation_uuid = self._parse_uuid(
                reservation_id,
                "reservation_id",
            )

            if input_tokens < 0:
                raise ValueError(
                    "input_tokens cannot be negative"
                )

            if output_tokens < 0:
                raise ValueError(
                    "output_tokens cannot be negative"
                )

            if total_tokens < 0:
                raise ValueError(
                    "total_tokens cannot be negative"
                )

            if total_tokens != (
                input_tokens + output_tokens
            ):
                raise ValueError(
                    "total_tokens must equal "
                    "input_tokens + output_tokens"
                )

            # ============================================================
            # LOCK RESERVATION
            # ============================================================

            reservation = await self._get_reservation(
                reservation_id=reservation_uuid,
                lock=True,
            )

            if reservation is None:
                raise ValueError(
                    "Token reservation not found"
                )

            # ============================================================
            # VERIFY OWNER
            # ============================================================

            if str(reservation.user_id) != str(user_id):
                raise ValueError(
                    "Reservation does not belong to user"
                )

            # ============================================================
            # IDEMPOTENCY
            #
            # A repeated settlement request must NOT charge again.
            # ============================================================

            if (
                reservation.status
                == TokenReservationStatus.SETTLED
            ):
                logger.info(
                    "Settlement already completed",
                    extra={
                        "user_id": user_id,
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                    },
                )

                wallet = await self._get_wallet(
                    user_id=user_id,
                    lock=False,
                )

                return SettleResult(
                    success=True,
                    charged_tokens=int(
                        reservation.actual_tokens or 0
                    ),
                    refunded_tokens=int(
                        reservation.refunded_tokens or 0
                    ),
                    remaining_tokens=(
                        int(wallet.available_tokens)
                        if wallet
                        else 0
                    ),
                    message="Reservation already settled",
                )

            # ============================================================
            # RELEASED RESERVATION CANNOT BE SETTLED
            # ============================================================

            if (
                reservation.status
                == TokenReservationStatus.RELEASED
            ):
                raise ValueError(
                    "Reservation has already been released"
                )

            # ============================================================
            # VERIFY REQUEST ID
            # ============================================================

            if reservation.request_id != request_id:
                raise ValueError(
                    "Request ID does not match reservation"
                )

            # ============================================================
            # CHECK RESERVATION EXPIRATION
            # ============================================================

            now = datetime.now(timezone.utc)

            if (
                reservation.status
                == TokenReservationStatus.EXPIRED
            ):
                raise ValueError(
                    "Token reservation has expired"
                )

            if reservation.expires_at <= now:
                raise ValueError(
                    "Token reservation has expired"
                )

            # ============================================================
            # VALIDATE ACTUAL USAGE
            # ============================================================

            reserved_tokens = int(
                reservation.reserved_tokens
            )

            if total_tokens > reserved_tokens:
                raise ValueError(
                    "Actual token usage exceeds reserved tokens"
                )

            # ============================================================
            # LOCK WALLET
            # ============================================================

            wallet = await self._get_wallet(
                user_id=user_id,
                lock=True,
            )

            if wallet is None:
                raise ValueError(
                    "Token wallet not found"
                )

            # ============================================================
            # CURRENT BALANCE
            #
            # At this point the reservation has already deducted
            # reserved_tokens from available_tokens.
            # ============================================================

            balance_before_refund = int(
                wallet.available_tokens
            )

            # ============================================================
            # CALCULATE REFUND
            # ============================================================

            refunded_tokens = (
                reserved_tokens
                - total_tokens
            )

            # ============================================================
            # RETURN UNUSED TOKENS
            # ============================================================

            wallet.available_tokens = (
                balance_before_refund
                + refunded_tokens
            )

            # ============================================================
            # COUNT ACTUAL USAGE
            # ============================================================

            wallet.lifetime_used_tokens = (
                int(wallet.lifetime_used_tokens)
                + total_tokens
            )

            balance_after_refund = int(
                wallet.available_tokens
            )

            # ============================================================
            # UPDATE RESERVATION
            # ============================================================

            reservation.status = (
                TokenReservationStatus.SETTLED
            )

            reservation.actual_tokens = (
                total_tokens
            )

            reservation.refunded_tokens = (
                refunded_tokens
            )

            reservation.input_tokens = (
                input_tokens
            )

            reservation.output_tokens = (
                output_tokens
            )

            reservation.settled_at = now

            # ============================================================
            # CONSUMPTION TRANSACTION
            #
            # This represents the actual tokens consumed.
            #
            # The wallet had already been reduced by the reservation,
            # so the balance_before value represents the balance
            # immediately before the refund is applied.
            # ============================================================

            consumption_transaction = TokenTransaction(
                id=uuid.uuid4(),
                user_id=user_id,
                reservation_id=reservation.id,
                request_id=request_id,
                type=TokenTransactionType.CONSUMPTION,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                balance_before=balance_before_refund,
                balance_after=balance_after_refund,
                model=model,
                created_at=now,
            )

            self.db.add(
                consumption_transaction
            )

            # ============================================================
            # REFUND TRANSACTION
            #
            # Record unused reserved tokens returned to wallet.
            # ============================================================

            if refunded_tokens > 0:

                refund_balance_before = (
                    balance_before_refund
                )

                refund_balance_after = (
                    balance_after_refund
                )

                refund_transaction = TokenTransaction(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    reservation_id=reservation.id,
                    request_id=request_id,
                    type=TokenTransactionType.REFUND,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=refunded_tokens,
                    balance_before=(
                        refund_balance_before
                    ),
                    balance_after=(
                        refund_balance_after
                    ),
                    model=model,
                    created_at=now,
                )

                self.db.add(
                    refund_transaction
                )

            # ============================================================
            # COMMIT ATOMICALLY
            # ============================================================

            try:
                await self.db.commit()

            except Exception:
                await self.db.rollback()

                logger.exception(
                    "Token settlement transaction failed",
                    extra={
                        "user_id": user_id,
                        "reservation_id": reservation_id,
                        "request_id": request_id,
                    },
                )

                raise

            # ============================================================
            # SUCCESS LOG
            # ============================================================

            logger.info(
                "Tokens settled successfully",
                extra={
                    "user_id": user_id,
                    "reservation_id": reservation_id,
                    "request_id": request_id,
                    "reserved_tokens": reserved_tokens,
                    "actual_tokens": total_tokens,
                    "refunded_tokens": refunded_tokens,
                    "remaining_tokens": (
                        wallet.available_tokens
                    ),
                },
            )

            # ============================================================
            # RESULT
            # ============================================================

            return SettleResult(
                success=True,
                charged_tokens=total_tokens,
                refunded_tokens=refunded_tokens,
                remaining_tokens=int(
                    wallet.available_tokens
                ),
                message="Tokens settled successfully",
            )


    # ========================================================
    # RELEASE TOKENS
    # ========================================================

    async def release_tokens(
        self,
        *,
        user_id: str,
        reservation_id: str,
        request_id: str,
    ) -> ReleaseResult:
        """
        Release a reservation.

        Used when the AI request fails.

        Example:

            wallet = 5,000
            reservation = 3,000

            LLM fails

            wallet = 8,000
            reservation = RELEASED
        """

        user_id = self._validate_user_id(user_id)
        request_id = self._validate_request_id(
            request_id
        )

        reservation_uuid = self._parse_uuid(
            reservation_id,
            "reservation_id",
        )

        # ----------------------------------------------------
        # Lock reservation.
        # ----------------------------------------------------

        reservation = await self._get_reservation(
            reservation_id=reservation_uuid,
            lock=True,
        )

        if reservation is None:
            raise ValueError(
                "Token reservation not found"
            )

        if reservation.user_id != user_id:
            raise ValueError(
                "Reservation does not belong to user"
            )

        if reservation.request_id != request_id:
            raise ValueError(
                "Request ID does not match reservation"
            )

        # ----------------------------------------------------
        # Idempotency.
        # ----------------------------------------------------

        if (
            reservation.status
            == TokenReservationStatus.RELEASED
        ):

            wallet = await self._get_wallet(
                user_id=user_id,
                lock=False,
            )

            return ReleaseResult(
                success=True,
                released_tokens=0,
                remaining_tokens=(
                    int(wallet.available_tokens)
                    if wallet
                    else 0
                ),
                message="Reservation already released",
            )

        if (
            reservation.status
            == TokenReservationStatus.SETTLED
        ):
            raise ValueError(
                "Cannot release a settled reservation"
            )

        # ----------------------------------------------------
        # Lock wallet.
        # ----------------------------------------------------

        wallet = await self._get_wallet(
            user_id=user_id,
            lock=True,
        )

        if wallet is None:
            raise ValueError(
                "Token wallet not found"
            )

        released_tokens = int(
            reservation.reserved_tokens
        )

        # ----------------------------------------------------
        # Return reserved tokens.
        # ----------------------------------------------------

        wallet.available_tokens = (
            int(wallet.available_tokens)
            + released_tokens
        )

        # ----------------------------------------------------
        # Update reservation.
        # ----------------------------------------------------

        reservation.status = (
            TokenReservationStatus.RELEASED
        )

        reservation.released_at = (
            datetime.now(timezone.utc)
        )

        # ----------------------------------------------------
        # Audit transaction.
        # ----------------------------------------------------

        balance_before = int(wallet.available_tokens)

        wallet.available_tokens = (
            balance_before + released_tokens
        )

        transaction = TokenTransaction(
            id=uuid4(),
            user_id=user_id,
            reservation_id=reservation.id,
            request_id=request_id,
            type=TokenTransactionType.RELEASE,
            input_tokens=0,
            output_tokens=0,
            total_tokens=released_tokens,
            balance_before=balance_before,
            balance_after=int(wallet.available_tokens),
            model=reservation.model,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(transaction)

        await self.db.commit()

        logger.info(
            "Tokens released successfully",
            extra={
                "user_id": user_id,
                "reservation_id": reservation_id,
                "request_id": request_id,
                "released_tokens": released_tokens,
                "remaining_tokens": (
                    wallet.available_tokens
                ),
            },
        )

        return ReleaseResult(
            success=True,
            released_tokens=released_tokens,
            remaining_tokens=int(
                wallet.available_tokens
            ),
            message="Tokens released successfully",
        )

    # ========================================================
    # EXPIRED RESERVATIONS
    # ========================================================

    async def release_expired_reservation(
        self,
        *,
        reservation_id: str,
    ) -> ReleaseResult:
        """
        Release an expired reservation.

        This is useful for a Celery/background cleanup task.

        If the Chat service crashes after reservation and
        before settlement/release, this prevents tokens from
        remaining locked forever.
        """

        reservation_uuid = self._parse_uuid(
            reservation_id,
            "reservation_id",
        )

        reservation = await self._get_reservation(
            reservation_id=reservation_uuid,
            lock=True,
        )

        if reservation is None:
            raise ValueError(
                "Token reservation not found"
            )

        if (
            reservation.status
            != TokenReservationStatus.PENDING
        ):
            wallet = await self._get_wallet(
                user_id=reservation.user_id,
                lock=False,
            )

            return ReleaseResult(
                success=True,
                released_tokens=0,
                remaining_tokens=(
                    int(wallet.available_tokens)
                    if wallet
                    else 0
                ),
                message="Reservation is no longer pending",
            )

        now = datetime.now(timezone.utc)

        if (
            reservation.expires_at is not None
            and reservation.expires_at > now
        ):
            raise ValueError(
                "Reservation has not expired"
            )

        wallet = await self._get_wallet(
            user_id=reservation.user_id,
            lock=True,
        )

        if wallet is None:
            raise ValueError(
                "Token wallet not found"
            )

        released_tokens = int(
            reservation.reserved_tokens
        )

        wallet.available_tokens = (
            int(wallet.available_tokens)
            + released_tokens
        )

        reservation.status = (
            TokenReservationStatus.EXPIRED
        )

        reservation.released_at = now

        transaction = TokenTransaction(
            id=uuid4(),
            user_id=reservation.user_id,
            reservation_id=reservation.id,
            request_id=reservation.request_id,
            type=TokenTransactionType.RELEASE,
            tokens=released_tokens,
            input_tokens=0,
            output_tokens=0,
            model=reservation.model,
            created_at=now,
        )

        self.db.add(transaction)

        await self.db.commit()

        logger.warning(
            "Expired token reservation released",
            extra={
                "user_id": reservation.user_id,
                "reservation_id": str(
                    reservation.id
                ),
                "released_tokens": released_tokens,
            },
        )

        return ReleaseResult(
            success=True,
            released_tokens=released_tokens,
            remaining_tokens=int(
                wallet.available_tokens
            ),
            message=(
                "Expired reservation released"
            ),
        )

    # ========================================================
    # INTERNAL DATABASE HELPERS
    # ========================================================

    async def _get_wallet(
        self,
        *,
        user_id: str,
        lock: bool,
    ) -> TokenWallet | None:
        """
        Fetch wallet.

        lock=True uses SELECT FOR UPDATE.

        This is critical when modifying the wallet.
        """

        query = (
            select(TokenWallet)
            .where(
                TokenWallet.user_id == user_id
            )
        )

        if lock:
            query = query.with_for_update()

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def _get_reservation(
        self,
        *,
        reservation_id: UUID,
        lock: bool,
    ) -> TokenReservation | None:
        """
        Fetch reservation.
        """

        query = (
            select(TokenReservation)
            .where(
                TokenReservation.id
                == reservation_id
            )
        )

        if lock:
            query = query.with_for_update()

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def _get_reservation_by_request_id(
        self,
        *,
        user_id: str,
        request_id: str,
    ) -> TokenReservation | None:
        """
        Find an existing reservation by idempotency key.

        IMPORTANT:
        request_id should have a UNIQUE constraint together
        with user_id at the database level.
        """

        result = await self.db.execute(
            select(TokenReservation)
            .where(
                TokenReservation.user_id
                == user_id,
                TokenReservation.request_id
                == request_id,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================
    # VALIDATION HELPERS
    # ========================================================

    @staticmethod
    def _validate_user_id(
        user_id: str,
    ) -> str:

        user_id = str(user_id).strip()

        if not user_id:
            raise ValueError(
                "user_id cannot be empty"
            )

        return user_id

    @staticmethod
    def _validate_request_id(
        request_id: str,
    ) -> str:

        request_id = str(request_id).strip()

        if not request_id:
            raise ValueError(
                "request_id cannot be empty"
            )

        return request_id

    @staticmethod
    def _parse_uuid(
        value: str,
        field_name: str,
    ) -> UUID:

        try:
            return UUID(str(value))

        except (ValueError, TypeError, AttributeError):

            raise ValueError(
                f"Invalid {field_name}"
            ) from None