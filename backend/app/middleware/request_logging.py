import time

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)
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

        request_id = getattr(
            request.state,
            "request_id",
            "-",
        )

        logger.info(

            "Incoming request | "

            "request_id=%s "

            "method=%s "

            "path=%s "

            "client=%s",

            request_id,

            request.method,

            request.url.path,

            request.client.host
            if request.client
            else "-",

        )

        try:

            response = await call_next(
                request
            )

        except Exception:

            logger.exception(

                "Unhandled exception | "

                "request_id=%s "

                "method=%s "

                "path=%s",

                request_id,

                request.method,

                request.url.path,

            )

            raise

        duration = (
            time.perf_counter()
            - start
        ) * 1000

        logger.info(

            "Request completed | "

            "request_id=%s "

            "status=%s "

            "duration=%.2fms",

            request_id,

            response.status_code,

            duration,

        )

        return response