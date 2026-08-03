from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings


def verify_google_token(token: str) -> dict[str, Any]:
    """
    Verify a Google ID token and return the decoded payload.

    Raises:
        HTTPException: If the token is invalid.
    """

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        if payload.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise ValueError("Invalid token issuer.")

        return payload

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token.",
        ) from exc