from fastapi import (
    Depends,
    Header,
    HTTPException,
    status,
)

from app.grpc.auth_client import AuthClient


auth_client = AuthClient()



async def get_current_user(
    authorization: str | None = Header(None),
):

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )


    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format",
        )


    token = authorization.replace(
        "Bearer ",
        "",
        1,
    )


    user = await auth_client.verify_token(
        token
    )


    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


    return user



async def require_admin(
    current_user=Depends(
        get_current_user
    ),
):

    if current_user.get("role") != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


    return current_user