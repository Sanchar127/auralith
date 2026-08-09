from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security import decode_access_token
from app.db.model.user import User
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.services.auth.user import AuthService


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
)


async def get_db_session() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    """
    FastAPI dependency that provides an async database session.
    """

    async for session in get_db():
        yield session


DBSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


async def get_current_user(
    token: str = Depends(
        oauth2_scheme,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
) -> User:
    """
    Return the authenticated user from an access token.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:

        payload = decode_access_token(
            token,
        )

        user_id = payload.get(
            "sub",
        )

        if user_id is None:

            logger.warning(
                "Authentication failed: token missing subject."
            )

            raise credentials_exception

    except JWTError:

        logger.warning(
            "Authentication failed: invalid or expired JWT."
        )

        raise credentials_exception

    except Exception:

        logger.exception(
            "Unexpected error while decoding access token."
        )

        raise credentials_exception

    repo = UserRepository(db)

    try:

        user = await repo.get_by_id(
            user_id,
        )

    except Exception:

        logger.exception(
            "Database error while loading user. user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable.",
        )

    if user is None:

        logger.warning(
            "Authentication failed: user not found. user_id=%s",
            user_id,
        )

        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(
        get_current_user,
    ),
) -> User:
    """
    Ensure the authenticated user is active.
    """

    if not current_user.is_active:

        logger.warning(
            "Inactive account attempted access. user_id=%s",
            current_user.id,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )

    return current_user


CurrentUser = Annotated[
    User,
    Depends(get_current_active_user),
]


OptionalCurrentUser = Annotated[
    User,
    Depends(get_current_user),
]


async def get_auth_service(
    db: DBSession,
) -> AuthService:
    """
    FastAPI dependency that provides an AuthService instance.
    """

    return AuthService(db)