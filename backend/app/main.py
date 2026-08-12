
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

from app.services.chat.memory import conversation_memory
from app.services.rag.pipeline import rag_pipeline
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

    # ==========================================
    # Initialize Redis
    # ==========================================

    try:
        logger.info("Connecting to Redis...")

        await conversation_memory.connect()

        logger.info(
            "Redis initialized successfully."
        )

    except Exception:
        logger.exception(
            "Redis initialization failed."
        )
        raise

    # ==========================================
    # Initialize Qdrant
    # ==========================================

    try:
        logger.info("Connecting to Qdrant...")

        await vector_store.connect()

        logger.info("Initializing Qdrant...")

        await vector_store.initialize()

        logger.info(
            "Qdrant initialized successfully."
        )

    except Exception:
        logger.exception(
            "Qdrant initialization failed."
        )

        await conversation_memory.close()

        raise

    # ==========================================
    # Initialize Ollama / RAG Pipeline
    # ==========================================

    try:
        logger.info(
            "Initializing RAG pipeline..."
        )

        rag_pipeline.connect()

        logger.info(
            "RAG pipeline initialized successfully."
        )

    except Exception:
        logger.exception(
            "RAG pipeline initialization failed."
        )

        await vector_store.close()
        await conversation_memory.close()

        raise

    # ==========================================
    # Start Auth gRPC Server
    # ==========================================

    logger.info(
        "Starting Auth gRPC server..."
    )

    grpc_task = asyncio.create_task(
        serve()
    )

    logger.info(
        "Auth gRPC server task started."
    )

    # ==========================================
    # Application running
    # ==========================================

    yield

    # ==========================================
    # Shutdown
    # ==========================================

    logger.info(
        "Shutting down backend..."
    )

    # ------------------------------------------
    # Stop gRPC
    # ------------------------------------------

    if grpc_task:
        grpc_task.cancel()

        try:
            await grpc_task

        except asyncio.CancelledError:
            logger.info(
                "Auth gRPC server stopped."
            )

    # ------------------------------------------
    # Close RAG / Ollama
    # ------------------------------------------

    try:
        await rag_pipeline.close()

    except Exception:
        logger.exception(
            "Failed to close RAG pipeline."
        )

    # ------------------------------------------
    # Close Qdrant
    # ------------------------------------------

    try:
        await vector_store.close()

    except Exception:
        logger.exception(
            "Failed to close Qdrant."
        )

    # ------------------------------------------
    # Close Redis
    # ------------------------------------------

    try:
        await conversation_memory.close()

    except Exception:
        logger.exception(
            "Failed to close Redis."
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


# ==========================================
# Middleware
# ==========================================

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


# ==========================================
# API Routes
# ==========================================

app.include_router(
    api_router,
    prefix="/api/v1",
)


# ==========================================
# Health Check
# ==========================================

@app.get("/")
async def health():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
    }
