from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import logger
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
        logger.info(
            "Generating tokens for user_id=%s ip=%s",
            user.id,
            ip,
        )
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
        logger.debug(
            "Refresh token persisted for user_id=%s",
            user.id,
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
        email = payload.email.lower()
        logger.info("Registration attempt for email=%s", email)
        try:
            existing = await self.users.get_by_email(email)
            if existing:
                logger.warning(
                    "Registration failed: email already registered email=%s",
                    email,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered.",
                )
            user = await self.users.create(
                email=email,
                full_name=payload.full_name,
                password_hash=hash_password(payload.password),
                provider=AuthProvider.LOCAL,
                is_active=True,
            )
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(
                "User registered successfully user_id=%s email=%s",
                user.id,
                email,
            )
            return UserResponse.model_validate(user)
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            logger.exception(
                "Unexpected error during registration email=%s",
                email,
            )
            raise

    async def login(
        self,
        payload: LoginRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        email = payload.email
        logger.info(
            "Login attempt email=%s ip=%s",
            email,
            ip,
        )
        try:
            user = await self.users.get_by_email(email)
            if not user:
                logger.warning(
                    "Login failed: user not found email=%s ip=%s",
                    email,
                    ip,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )
            if user.password_hash is None:
                logger.warning(
                    "Login failed: no local password (use Google) user_id=%s email=%s",
                    user.id,
                    email,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Use Google Sign-In.",
                )
            if not verify_password(
                payload.password,
                user.password_hash,
            ):
                logger.warning(
                    "Login failed: invalid password user_id=%s email=%s ip=%s",
                    user.id,
                    email,
                    ip,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )
            if not user.is_active:
                logger.warning(
                    "Login failed: account disabled user_id=%s email=%s",
                    user.id,
                    email,
                )
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
            logger.info(
                "Login successful user_id=%s email=%s ip=%s",
                user.id,
                email,
                ip,
            )
            return tokens
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            logger.exception(
                "Unexpected error during login email=%s ip=%s",
                email,
                ip,
            )
            raise

    async def google_login(
        self,
        payload: GoogleLoginRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        logger.info("Google login attempt ip=%s", ip)
        try:
            google_user = verify_google_token(
                payload.id_token
            )
            email = google_user["email"]
            logger.debug(
                "Google token verified email=%s sub=%s",
                email,
                google_user.get("sub"),
            )
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
                logger.info(
                    "New user created via Google login user_id=%s email=%s",
                    user.id,
                    email,
                )
            else:
                if user.google_id is None:
                    user.google_id = google_user["sub"]
                    if user.provider == AuthProvider.LOCAL:
                        user.provider = AuthProvider.BOTH
                    logger.info(
                        "Linked Google account to existing user user_id=%s email=%s",
                        user.id,
                        email,
                    )
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
            logger.info(
                "Google login successful user_id=%s email=%s ip=%s",
                user.id,
                email,
                ip,
            )
            return tokens
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            logger.exception(
                "Unexpected error during Google login ip=%s",
                ip,
            )
            raise