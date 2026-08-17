import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import logger


class RequestLoggingMiddleware(
    BaseHTTPMiddleware,
):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        start = time.perf_counter()

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client=(
                request.client.host
                if request.client
                else None
            ),
        )

        try:
            response = await call_next(
                request
            )

        except Exception:
            duration_ms = (
                time.perf_counter()
                - start
            ) * 1000

            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(
                    duration_ms,
                    2,
                ),
            )

            raise

        duration_ms = (
            time.perf_counter()
            - start
        ) * 1000

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(
                duration_ms,
                2,
            ),
        )

        response.headers[
            "X-Request-ID"
        ] = request.state.request_id

        return response