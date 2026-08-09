from fastapi import Request

from app.grpc.auth_client import AuthClient


def get_auth_client(
    request: Request,
) -> AuthClient:

    return request.app.state.auth_client