from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.db.model.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):

    model = User


    async def get_by_id(
        self,
        user_id: UUID | str,
    ) -> User | None:

        stmt = (
            select(User)
            .where(User.id == user_id)
        )

        result = await self.session.execute(
            stmt
        )

        return result.scalar_one_or_none()



    async def get_by_email(
        self,
        email: str,
    ) -> User | None:

        stmt = (
            select(User)
            .where(
                User.email == email.lower()
            )
        )

        result = await self.session.execute(
            stmt
        )

        return result.scalar_one_or_none()



    async def get_by_google_id(
        self,
        google_id: str,
    ) -> User | None:

        stmt = (
            select(User)
            .where(
                User.google_id == google_id
            )
        )

        result = await self.session.execute(
            stmt
        )

        return result.scalar_one_or_none()



    async def exists(
        self,
        email: str,
    ) -> bool:

        user = await self.get_by_email(
            email
        )

        return user is not None



    async def mark_verified(
        self,
        user: User,
    ) -> User:

        user.is_verified = True

        return await self.save(
            user
        )



    async def update_last_login(
        self,
        user: User,
    ) -> User:

        user.last_login_at = datetime.now(
            UTC
        )

        return await self.save(
            user
        )



    async def activate(
        self,
        user: User,
    ) -> User:

        user.is_active = True

        return await self.save(
            user
        )



    async def deactivate(
        self,
        user: User,
    ) -> User:

        user.is_active = False

        return await self.save(
            user
        )