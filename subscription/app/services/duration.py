from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.subscriptions import SubscriptionDuration

from app.repositories.duration import (
    SubscriptionDurationRepository,
)

from app.schemas.duration import (
    SubscriptionDurationCreate,
    SubscriptionDurationUpdate,
)


class SubscriptionDurationService:


    def __init__(
        self,
        db: AsyncSession,
    ):

        self.repo = SubscriptionDurationRepository(
            db
        )


    async def create_duration(
        self,
        payload: SubscriptionDurationCreate,
    ):

        existing = await self.repo.get_by_name(
            payload.name
        )

        if existing:
            raise ValueError(
                "Duration already exists"
            )


        duration = SubscriptionDuration(
            name=payload.name,
            duration_months=payload.duration_months,
            discount_percentage=payload.discount_percentage,
            is_active=payload.is_active,
        )


        await self.repo.create(
            duration
        )

        await self.repo.commit()

        await self.repo.refresh(
            duration
        )

        return duration



    async def get_duration(
        self,
        duration_id: uuid.UUID,
    ):

        return await self.repo.get_by_id(
            duration_id
        )


    async def list_durations(
        self,
        active_only: bool=False,
    ):

        if active_only:
            return await self.repo.get_active()

        return await self.repo.get_all()



    async def update_duration(
        self,
        duration_id: uuid.UUID,
        payload: SubscriptionDurationUpdate,
    ):


        duration = await self.repo.get_by_id(
            duration_id
        )


        if duration is None:
            return None


        values = payload.model_dump(
            exclude_unset=True
        )


        for key,value in values.items():

            setattr(
                duration,
                key,
                value
            )


        await self.repo.commit()

        await self.repo.refresh(
            duration
        )


        return duration



    async def delete_duration(
        self,
        duration_id: uuid.UUID,
    ):


        duration = await self.repo.get_by_id(
            duration_id
        )


        if duration is None:
            return None


        await self.repo.delete(
            duration
        )

        await self.repo.commit()

        return True