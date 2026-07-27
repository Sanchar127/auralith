from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import logger
from app.services.rag.vector_store import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle events.
    """

    logger.info("🚀 Starting Auralith Backend...")

    # Create Qdrant collection if it doesn't exist
    await vector_store.initialize()

    logger.info("✅ Qdrant initialized.")

    yield

    logger.info("🛑 Shutting down Auralith Backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Music Generation Platform",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(
    api_router,
    prefix="/api/v1",
)