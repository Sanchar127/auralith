
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AudioJobType(str, enum.Enum):
    ENHANCE = "enhance"


class AudioJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioJob(Base):
    __tablename__ = "audio_jobs"

    # =========================================================
    # Primary Key
    # =========================================================

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # =========================================================
    # Ownership
    # =========================================================

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    # =========================================================
    # Job Information
    # =========================================================

    job_type: Mapped[AudioJobType] = mapped_column(
        Enum(
            AudioJobType,
            name="audio_job_type",
        ),
        nullable=False,
    )

    status: Mapped[AudioJobStatus] = mapped_column(
        Enum(
            AudioJobStatus,
            name="audio_job_status",
        ),
        nullable=False,
        default=AudioJobStatus.QUEUED,
        index=True,
    )

    # =========================================================
    # MinIO Objects
    # =========================================================

    input_object_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    output_object_key: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # =========================================================
    # Celery
    # =========================================================

    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # =========================================================
    # Error
    # =========================================================

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =========================================================
    # Timestamps
    # =========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =========================================================
    # Relationships
    # =========================================================

    user = relationship(
        "User",
        back_populates="audio_jobs",
    )

    conversation = relationship(
        "Conversation",
        back_populates="audio_jobs",
    )

