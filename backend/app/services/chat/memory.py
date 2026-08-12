
from __future__ import annotations

import json

import redis.asyncio as redis

from app.core.config import settings
from app.core.logger import logger


class ConversationMemory:
    """
    Redis-backed conversation memory.

    Stores the most recent messages for each conversation.
    """

    def __init__(self) -> None:
        self.redis: redis.Redis | None = None

        self.max_messages = 20
        self.ttl = 60 * 60 * 24

    # ==========================================================
    # Connection lifecycle
    # ==========================================================

    async def connect(self) -> None:
        """Create and verify the Redis client."""

        if self.redis is not None:
            return

        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

        await self.redis.ping()

        logger.info(
            "Connected to Redis at %s",
            settings.REDIS_URL,
        )

    async def close(self) -> None:
        """Close the Redis client."""

        if self.redis is None:
            return

        await self.redis.aclose()

        self.redis = None

        logger.info(
            "Redis client closed."
        )

    def _get_client(self) -> redis.Redis:
        """Return the initialized Redis client."""

        if self.redis is None:
            raise RuntimeError(
                "Redis client is not initialized. "
                "Call connect() first."
            )

        return self.redis

    # ==========================================================
    # Key
    # ==========================================================

    def _key(
        self,
        conversation_id: str,
    ) -> str:
        return f"chat:{conversation_id}"

    # ==========================================================
    # Save
    # ==========================================================

    async def save(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:

        client = self._get_client()

        key = self._key(conversation_id)

        message = {
            "role": role,
            "content": content,
        }

        await client.rpush(
            key,
            json.dumps(message),
        )

        while await client.llen(key) > self.max_messages:
            await client.lpop(key)

        await client.expire(
            key,
            self.ttl,
        )

        logger.debug(
            "Conversation updated: %s",
            conversation_id,
        )

    # ==========================================================
    # Load
    # ==========================================================

    async def load(
        self,
        conversation_id: str,
    ) -> list[dict]:
        client = self._get_client()

        key = self._key(conversation_id)

        items = await client.lrange(
            key,
            0,
            -1,
        )

        return [
            json.loads(item)
            for item in items
        ]

    # ==========================================================
    # Clear
    # ==========================================================

    async def clear(
        self,
        conversation_id: str,
    ) -> None:

        client = self._get_client()

        await client.delete(
            self._key(conversation_id)
        )

        logger.info(
            "Conversation cleared: %s",
            conversation_id,
        )

    # ==========================================================
    # Backward compatibility
    # ==========================================================

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:

        await self.save(
            conversation_id,
            role,
            content,
        )

    async def get_messages(
        self,
        conversation_id: str,
    ) -> list[dict]:

        return await self.load(
            conversation_id,
        )


conversation_memory = ConversationMemory()
