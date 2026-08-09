from fastapi import (
    APIRouter,
    Depends,
    Request,
    status,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from app.core.dependencies import (
    CurrentUser,
    get_auth_service,
)
from app.core.logger import logger
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth.user import AuthService


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ==========================================================
# Register
# ==========================================================

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
    Register a new account.
    """

    logger.info(
        "Registration request received email=%s",
        payload.email,
    )

    user = await auth_service.register(
        payload,
    )

    logger.info(
        "Registration completed user_id=%s",
        user.id,
    )

    return user


# ==========================================================
# Login (JSON)
# ==========================================================

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
    Login using JSON payload.
    """

    logger.info(
        "Login request email=%s",
        payload.email,
    )

    token = await auth_service.login(
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "Login successful email=%s",
        payload.email,
    )

    return token


# ==========================================================
# OAuth2 Login (Swagger)
# ==========================================================

@router.post(
    "/token",
    response_model=TokenResponse,
)
async def token_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    OAuth2 password flow endpoint for Swagger UI.
    """

    logger.info(
        "OAuth2 login request username=%s",
        form_data.username,
    )

    payload = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )

    token = await auth_service.login(
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "OAuth2 login successful username=%s",
        form_data.username,
    )

    return token


# ==========================================================
# Google Login
# ==========================================================

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
    Google OAuth login.
    """

    logger.info(
        "Google login request received."
    )

    token = await auth_service.google_login(
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    logger.info(
        "Google login successful."
    )

    return token


# ==========================================================
# Refresh Token
# ==========================================================

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

    logger.info(
        "Refresh token request received."
    )

    token = await auth_service.refresh_token(
        payload,
    )

    logger.info(
        "Access token refreshed successfully."
    )

    return token


# ==========================================================
# Logout
# ==========================================================

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

    logger.info(
        "Logout request user_id=%s",
        current_user.id,
    )

    await auth_service.logout(
        current_user=current_user,
        refresh_token=refresh_token.refresh_token,
    )

    logger.info(
        "Logout completed user_id=%s",
        current_user.id,
    )


# ==========================================================
# Logout All
# ==========================================================

@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_all(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout all active sessions.
    """

    logger.info(
        "Logout-all request user_id=%s",
        current_user.id,
    )

    await auth_service.logout_all(
        current_user,
    )

    logger.info(
        "Logout-all completed user_id=%s",
        current_user.id,
    )


# ==========================================================
# Current User
# ==========================================================

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

    logger.debug(
        "Current user requested profile user_id=%s",
        current_user.id,
    )

    return current_user