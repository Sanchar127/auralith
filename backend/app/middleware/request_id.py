from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        request_id = request.headers.get(
            "X-Request-ID"
        ) or str(uuid4())

        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(
            request_id=request_id
        )

        try:
            response = await call_next(request)

            response.headers["X-Request-ID"] = request_id

            return response

        finally:
            structlog.contextvars.clear_contextvars()