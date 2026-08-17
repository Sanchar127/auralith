from __future__ import annotations

import time
from typing import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)


class PrometheusMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        service: str,
    ) -> None:
        self.app = app
        self.service = service

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:

        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )
            return

        method = scope["method"]

        start = time.perf_counter()

        HTTP_REQUESTS_IN_PROGRESS.labels(
            service=self.service,
        ).inc()

        status_code = 500

        async def send_wrapper(
            message: Message,
        ) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_wrapper,
            )

        finally:
            duration = (
                time.perf_counter()
                - start
            )

            route = self._get_route(scope)

            HTTP_REQUESTS_TOTAL.labels(
                service=self.service,
                method=method,
                route=route,
                status_code=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=self.service,
                method=method,
                route=route,
            ).observe(duration)

            HTTP_REQUESTS_IN_PROGRESS.labels(
                service=self.service,
            ).dec()

    @staticmethod
    def _get_route(scope: Scope) -> str:
        route = scope.get("route")

        if route is not None:
            path = getattr(
                route,
                "path",
                None,
            )

            if path:
                return path

        return scope.get(
            "path",
            "unknown",
        )