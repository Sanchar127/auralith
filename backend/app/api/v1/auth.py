from fastapi import APIRouter, Depends, Request, status

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    GoogleLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth.user import AuthService

from app.core.dependencies import (
    CurrentUser,
    get_auth_service,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user using email/password.
    """

    return await auth_service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login using email/password.
    """

    return await auth_service.login(
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/google",
    response_model=TokenResponse,
)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login using Google OAuth.
    """

    return await auth_service.google_login(
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh_token(
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token.
    """

    return await auth_service.refresh_token(payload)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    refresh_token: RefreshTokenRequest,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout current device.
    """

    await auth_service.logout(
        current_user=current_user,
        refresh_token=refresh_token.refresh_token,
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout all devices.
    """

    await auth_service.logout_all(current_user)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: CurrentUser,
):
    """
    Return authenticated user.
    """

    return current_user