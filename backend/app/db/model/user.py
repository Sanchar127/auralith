
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    BOTH = "both"


class User(Base):
    __tablename__ = "users"

    # =========================================================
    # Primary Key
    # =========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # =========================================================
    # Authentication
    # =========================================================

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    picture: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    # IMPORTANT:
    # The existing PostgreSQL enum is named "authprovider".
    # Keep this name so Alembic does not try to rename it.

    provider: Mapped[AuthProvider] = mapped_column(
        Enum(
            AuthProvider,
            name="authprovider",
        ),
        default=AuthProvider.LOCAL,
        nullable=False,
    )

    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    # =========================================================
    # Account Status
    # =========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # =========================================================
    # Login / Timestamps
    # =========================================================

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =========================================================
    # Relationships
    # =========================================================

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    audio_jobs = relationship(
        "AudioJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )
