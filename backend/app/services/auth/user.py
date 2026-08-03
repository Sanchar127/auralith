from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.oauth import verify_google_token
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.model.user import (
    AuthProvider,
    User,
)
from app.repositories.refresh_token import (
    RefreshTokenRepository,
)
from app.repositories.user import UserRepository
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    async def _generate_tokens(
        self,
        user: User,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        access_token = create_access_token(
            subject=str(user.id)
        )

        refresh_token = create_refresh_token(
            subject=str(user.id)
        )

        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip,
            user_agent=user_agent,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register(
        self,
        payload: RegisterRequest,
    ) -> UserResponse:
        try:
            existing = await self.users.get_by_email(
                payload.email
            )

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                )

            user = await self.users.create(
                email=payload.email.lower(),
                full_name=payload.full_name,
                password_hash=hash_password(payload.password),
                provider=AuthProvider.LOCAL,
                is_active=True,
            )

            await self.db.commit()
            await self.db.refresh(user)

            return UserResponse.model_validate(user)

        except HTTPException:
            await self.db.rollback()
            raise

        except Exception:
            await self.db.rollback()
            raise

    async def login(
        self,
        payload: LoginRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        try:
            user = await self.users.get_by_email(
                payload.email
            )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )

            if user.password_hash is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Use Google Sign-In.",
                )

            if not verify_password(
                payload.password,
                user.password_hash,
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account disabled.",
                )

            await self.users.update_last_login(user)

            tokens = await self._generate_tokens(
                user,
                ip,
                user_agent,
            )

            await self.db.commit()

            return tokens

        except HTTPException:
            await self.db.rollback()
            raise

        except Exception:
            await self.db.rollback()
            raise

    async def google_login(
        self,
        payload: GoogleLoginRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        try:
            google_user = verify_google_token(
                payload.id_token
            )

            email = google_user["email"]

            user = await self.users.get_by_email(email)

            if user is None:
                user = await self.users.create(
                    email=email,
                    full_name=google_user.get("name", ""),
                    picture=google_user.get("picture"),
                    google_id=google_user["sub"],
                    provider=AuthProvider.GOOGLE,
                    is_verified=True,
                    is_active=True,
                )
            else:
                if user.google_id is None:
                    user.google_id = google_user["sub"]

                    if user.provider == AuthProvider.LOCAL:
                        user.provider = AuthProvider.BOTH

                user.picture = google_user.get(
                    "picture",
                    user.picture,
                )

                await self.users.save(user)

            await self.users.update_last_login(user)

            tokens = await self._generate_tokens(
                user,
                ip,
                user_agent,
            )

            await self.db.commit()

            return tokens

        except HTTPException:
            await self.db.rollback()
            raise

        except Exception:
            await self.db.rollback()
            raise