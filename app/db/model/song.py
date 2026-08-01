from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class FileType(str, Enum):
    JSON = "json"
    MIDI = "midi"
    WAV = "wav"
    MP3 = "mp3"


class SongFile(Base):
    __tablename__ = "song_files"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: uuid4().hex,
    )

    song_id: Mapped[str] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"),
    )

    file_type: Mapped[FileType] = mapped_column(
        SQLEnum(FileType),
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    user_id = mapped_column(
    ForeignKey("users.id"),
    nullable=False,
    index=True,
)

    conversation_id = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )

    prompt_message_id = mapped_column(
        ForeignKey("messages.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    song = relationship(
        "Song",
        back_populates="files",
    )

    user = relationship(
    "User",
    back_populates="songs",
    )

    conversation = relationship(
        "Conversation",
        back_populates="songs",
    )

    prompt_message = relationship(
        "Message",
    )