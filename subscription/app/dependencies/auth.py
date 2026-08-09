
from __future__ import annotations

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.grpc.auth_client import AuthClient
from app.dependencies.auth_client import get_auth_client


# =========================================================
# HTTP Bearer Security
# =========================================================

security = HTTPBearer(
    auto_error=False,
)


# =========================================================
# Current User
# =========================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        security,
    ),
    auth_client: AuthClient = Depends(
        get_auth_client,
    ),
):

    if credentials is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )


    if credentials.scheme.lower() != "bearer":

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )


    token = credentials.credentials


    user = await auth_client.verify_token(
        token,
    )


    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


    return user


# =========================================================
# Admin
# =========================================================

async def require_admin(
    current_user=Depends(
        get_current_user,
    ),
):

    if "admin" not in current_user.get(
        "roles",
        [],
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


    return current_user

