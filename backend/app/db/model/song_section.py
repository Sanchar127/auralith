from __future__ import annotations



from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class SongSection(Base):
    __tablename__ = "song_sections"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: uuid4().hex,
    )

    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_index: Mapped[int] = mapped_column(Integer)

    name: Mapped[str] = mapped_column(String(100))

    lyrics: Mapped[list] = mapped_column(JSON)

    chords: Mapped[list] = mapped_column(JSON)

    melody: Mapped[list] = mapped_column(JSON)

    song = relationship(
        "Song",
        back_populates="sections",
    )