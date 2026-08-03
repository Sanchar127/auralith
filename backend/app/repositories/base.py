from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic SQLAlchemy repository.

    Responsibilities:
        - CRUD
        - Query helpers

    Does NOT:
        - Commit transactions
        - Handle business logic
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> ModelType:
        obj = self.model(**kwargs)

        self.session.add(obj)

        await self.session.flush()

        await self.session.refresh(obj)

        return obj

    async def get(
        self,
        object_id: UUID,
    ) -> ModelType | None:

        result = await self.session.execute(
            select(self.model).where(
                self.model.id == object_id
            )
        )

        return result.scalar_one_or_none()

    async def save(
        self,
        obj: ModelType,
    ) -> ModelType:

        self.session.add(obj)

        await self.session.flush()

        await self.session.refresh(obj)

        return obj

    async def delete(
        self,
        obj: ModelType,
    ) -> None:

        await self.session.delete(obj)

        await self.session.flush()