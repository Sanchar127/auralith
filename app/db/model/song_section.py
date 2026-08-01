from __future__ import annotations

from uuid import uuid4

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class SongSection(Base):
    __tablename__ = "song_sections"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=lambda: uuid4().hex,
    )

    song_id: Mapped[str] = mapped_column(
        ForeignKey("songs.id", ondelete="CASCADE"),
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