from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    genre: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    mood: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tempo: Mapped[int] = mapped_column(
        Integer,
        default=120,
        nullable=False,
    )

    key: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="completed",
        nullable=False,
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

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    # --------------------------------------------------
# Relationships
# --------------------------------------------------

    user = relationship(
        "User",
        back_populates="songs",
    )

    
    conversation = relationship(
        "Conversation",
        back_populates="songs",
    )

    sections = relationship(
        "SongSection",
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="SongSection.order_index",
    )

    files = relationship(
        "SongFile",
        back_populates="song",
        cascade="all, delete-orphan",
    )

    jobs = relationship(
        "GenerationJob",
        back_populates="song",
        cascade="all, delete-orphan",
    )

    