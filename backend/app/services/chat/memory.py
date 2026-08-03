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

    def __init__(self):

        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )

        self.max_messages = 20
        self.ttl = 60 * 60 * 24

    def _key(
        self,
        conversation_id: str,
    ) -> str:

        return f"chat:{conversation_id}"

    async def save(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:

        key = self._key(conversation_id)

        message = {
            "role": role,
            "content": content,
        }

        await self.redis.rpush(
            key,
            json.dumps(message),
        )

        while await self.redis.llen(key) > self.max_messages:
            await self.redis.lpop(key)

        await self.redis.expire(
            key,
            self.ttl,
        )

        logger.debug(
            "Conversation updated: %s",
            conversation_id,
        )

    async def load(
        self,
        conversation_id: str,
    ) -> list[dict]:

        key = self._key(conversation_id)

        items = await self.redis.lrange(
            key,
            0,
            -1,
        )

        return [
            json.loads(item)
            for item in items
        ]

    async def clear(
        self,
        conversation_id: str,
    ) -> None:

        await self.redis.delete(
            self._key(conversation_id)
        )

        logger.info(
            "Conversation cleared: %s",
            conversation_id,
        )

    # Backward compatibility
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