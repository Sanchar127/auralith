from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import logger

from app.grpc.auth_server import serve

from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

from app.services.rag.vector_store import vector_store


grpc_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    global grpc_task

    logger.info(
        "Starting %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )


    # ---------------------------------
    # Initialize Qdrant
    # ---------------------------------

    try:

        logger.info(
            "Initializing Qdrant..."
        )

        await vector_store.initialize()

        logger.info(
            "Qdrant initialized successfully."
        )


    except Exception:

        logger.exception(
            "Qdrant initialization failed."
        )

        raise



    # ---------------------------------
    # Start Auth gRPC Server
    # ---------------------------------

    logger.info(
        "Starting Auth gRPC server..."
    )


    grpc_task = asyncio.create_task(
        serve()
    )


    logger.info(
        "Auth gRPC server task started."
    )


    yield



    # ---------------------------------
    # Shutdown
    # ---------------------------------

    logger.info(
        "Shutting down backend..."
    )


    if grpc_task:

        grpc_task.cancel()

        try:

            await grpc_task

        except asyncio.CancelledError:

            logger.info(
                "Auth gRPC server stopped."
            )


    logger.info(
        "Backend shutdown complete."
    )



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Music Generation Platform",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)



# ---------------------------------
# Middleware
# ---------------------------------

app.add_middleware(
    RequestIDMiddleware
)


app.add_middleware(
    RequestLoggingMiddleware
)


app.add_middleware(
    SecurityHeadersMiddleware
)


app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------------------------
# API Routes
# ---------------------------------

app.include_router(
    api_router,
    prefix="/api/v1",
)



# ---------------------------------
# Health Check
# ---------------------------------

@app.get("/")
async def health():

    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
    }