from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TokenTransactionType(str, enum.Enum):
    CHAT = "chat"
    IMAGE = "image"
    AUDIO = "audio"
    PURCHASE = "purchase"
    REFUND = "refund"
    BONUS = "bonus"


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    nullable=True,
    index=True,
    )

    type: Mapped[TokenTransactionType] = mapped_column(
        Enum(TokenTransactionType),
    )

    model: Mapped[str] = mapped_column(
        String(100),
    )

    input_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
    )

    output_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
    )

    total_tokens: Mapped[int] = mapped_column(
        BigInteger,
    )

    balance_before: Mapped[int] = mapped_column(
        BigInteger,
    )

    balance_after: Mapped[int] = mapped_column(
        BigInteger,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    