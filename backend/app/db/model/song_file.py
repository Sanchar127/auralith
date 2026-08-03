from uuid import uuid4

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class SongFile(Base):
    __tablename__ = "song_files"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    song_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        index=True,
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
    )

    object_key: Mapped[str] = mapped_column(
        String(500),
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
    )

    song = relationship(
        "Song",
        back_populates="files",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )