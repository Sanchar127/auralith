from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import select

from app.db.model.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(
    BaseRepository[RefreshToken]
):

    model = RefreshToken

    async def get_by_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:

        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash
                == token_hash
            )
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_active(
        self,
        token_hash: str,
    ) -> RefreshToken | None:

        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash
                == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def revoke(
        self,
        token: RefreshToken,
    ) -> RefreshToken:

        token.revoked_at = datetime.now(UTC)

        return await self.save(token)

    async def revoke_all(
        self,
        user_id,
    ) -> None:

        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )

        result = await self.session.execute(stmt)

        tokens = result.scalars().all()

        now = datetime.now(UTC)

        for token in tokens:
            token.revoked_at = now

        await self.session.flush()