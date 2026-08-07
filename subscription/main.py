from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.durations import router as duration_router
from app.api.plans import router as plans_router
from app.api.subscriptions import router as subscriptions_router
from app.api.token_transactions import router as transaction_router
from app.api.wallets import router as wallet_router
from app.core.logger import logger
from app.grpc.server import serve


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Subscription Service..."
    )

    grpc_task = asyncio.create_task(
        serve()
    )

    logger.info(
        "gRPC server task created."
    )

    yield

    logger.info(
        "Stopping Subscription Service..."
    )

    grpc_task.cancel()

    try:
        await grpc_task
    except asyncio.CancelledError:
        logger.info(
            "gRPC server stopped."
        )


app = FastAPI(
    title="Auralith Subscription Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------

app.include_router(
    subscriptions_router,
    prefix="/api/v1",
)

app.include_router(
    duration_router,
    prefix="/api/v1",
)

app.include_router(
    plans_router,
    prefix="/api/v1",
)

app.include_router(
    wallet_router,
    prefix="/api/v1",
)

app.include_router(
    transaction_router,
    prefix="/api/v1",
)


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/")
async def health():
    logger.info(
        "Health endpoint called."
    )

    return {
        "service": "subscription",
        "status": "running",
    }