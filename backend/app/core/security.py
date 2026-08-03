from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings


# --------------------------------------------------
# Password Hashing
# --------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# --------------------------------------------------
# OAuth2
# --------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


# --------------------------------------------------
# Refresh Token Hash
# --------------------------------------------------

def hash_token(token: str) -> str:
    """
    Never store refresh tokens in plain text.
    """

    return hashlib.sha256(
        token.encode()
    ).hexdigest()


# --------------------------------------------------
# JWT
# --------------------------------------------------

def _build_payload(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:

    now = datetime.now(UTC)

    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
    }

    if extra:
        payload.update(extra)

    return payload


def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
) -> str:

    payload = _build_payload(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        extra=extra,
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """
    Decode and validate an access token.
    """

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise JWTError("Invalid access token")

    return payload

def create_refresh_token(
    subject: str,
) -> str:

    payload = _build_payload(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(
    token: str,
) -> dict[str, Any]:

    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


def verify_access_token(
    token: str,
) -> dict[str, Any]:

    payload = decode_token(token)

    if payload["type"] != "access":
        raise JWTError("Invalid access token")

    return payload


def verify_refresh_token(
    token: str,
) -> dict[str, Any]:

    payload = decode_token(token)

    if payload["type"] != "refresh":
        raise JWTError("Invalid refresh token")

    return payload


# --------------------------------------------------
# Random Token
# --------------------------------------------------

def generate_secure_token(
    length: int = 64,
) -> str:
    """
    Used for email verification,
    password reset,
    OTP secrets, etc.
    """

    return secrets.token_urlsafe(length)