"""
Register all SQLAlchemy ORM models.

Importing this package automatically registers every model with
Base.metadata so Alembic can discover them during migrations.
"""

from app.db.model.conversation import Conversation
from app.db.model.generation_job import GenerationJob
from app.db.model.message import Message
from app.db.model.refresh_token import RefreshToken
from app.db.model.song import Song
from app.db.model.song_file import SongFile
from app.db.model.song_section import SongSection
from app.db.model.user import User
from app.db.model.subscriptions import SubscriptionDuration,SubscriptionPlan
from app.db.model.token_wallet import TokenWallet
from app.db.model.tokentransaction import TokenTransaction,TokenTransactionType
from app.db.model.usersubscription import SubscriptionStatus,UserSubscription
__all__ = [
    "User",
    "RefreshToken",
    "Conversation",
    "Message",
    "Song",
    "SongSection",
    "SongFile",
    "GenerationJob",
    "SubscriptionDuration",
    "SubscriptionPlan",
    "TokenTransaction",
    "TokenWallet",
    "TokenTransactionType",
    "SubscriptionStatus",
    "UserSubscription"


]