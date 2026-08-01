"""
Register all SQLAlchemy ORM models.

Importing this package automatically registers every model with
Base.metadata so Alembic can discover them during migrations.
"""

from app.db.model.conversation import Conversation
from app.db.model.generation_job import GenerationJob
from app.db.model.message import Message
from app.db.model.song import Song
from app.db.model.song_file import SongFile
from app.db.model.song_section import SongSection
from app.db.model.user import User

__all__ = [
    "User",
    "Conversation",
    "Message",
    "Song",
    "SongSection",
    "SongFile",
    "GenerationJob",
]