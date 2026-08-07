from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionDuration


class SubscriptionDurationRepository:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db


    async def get_by_id(
        self,
        duration_id: uuid.UUID,
    ) -> SubscriptionDuration | None:

        result = await self.db.execute(
            select(SubscriptionDuration)
            .where(
                SubscriptionDuration.id == duration_id
            )
        )

        return result.scalar_one_or_none()


    async def get_by_name(
        self,
        name: str,
    ) -> SubscriptionDuration | None:

        result = await self.db.execute(
            select(SubscriptionDuration)
            .where(
                SubscriptionDuration.name == name
            )
        )

        return result.scalar_one_or_none()


    async def get_all(
        self,
    ) -> list[SubscriptionDuration]:

        result = await self.db.execute(
            select(SubscriptionDuration)
        )

        return result.scalars().all()


    async def get_active(
        self,
    ) -> list[SubscriptionDuration]:

        result = await self.db.execute(
            select(SubscriptionDuration)
            .where(
                SubscriptionDuration.is_active.is_(True)
            )
        )

        return result.scalars().all()


    async def create(
        self,
        duration: SubscriptionDuration,
    ):

        self.db.add(duration)

        await self.db.flush()

        return duration


    async def delete(
        self,
        duration: SubscriptionDuration,
    ):

        await self.db.delete(duration)


    async def commit(self):

        await self.db.commit()


    async def refresh(
        self,
        obj,
    ):

        await self.db.refresh(obj)