from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    APP_NAME: str = Field(default="Auralith")
    APP_VERSION: str = Field(default="0.1.0")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    DATABASE_URL: str = Field(default="")

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------

    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
    )

    # ------------------------------------------------------------------
    # RabbitMQ / Celery
    # ------------------------------------------------------------------

    CELERY_BROKER_URL: str = Field(default="")
    CELERY_RESULT_BACKEND: str = Field(default="")

    # ------------------------------------------------------------------
    # Ollama
    # ------------------------------------------------------------------

    OLLAMA_BASE_URL: str = Field(
        default="http://ollama:11434",
    )

    OLLAMA_MODEL: str = Field(
        default="llama3.2",
    )

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    OLLAMA_EMBED_MODEL: str = Field(
        default="nomic-embed-text",
    )

    # ------------------------------------------------------------------
    # Qdrant (Vector Database)
    # ------------------------------------------------------------------

    QDRANT_URL: str = Field(
        default="http://qdrant:6333",
    )

    QDRANT_COLLECTION: str = Field(
        default="knowledge",
    )

    QDRANT_VECTOR_SIZE: int = Field(
        default=768,
    )

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    SECRET_KEY: str = Field(
        default="change-me",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
    )

    # ------------------------------------------------------------------
    # MinIO
    # ------------------------------------------------------------------

    MINIO_ENDPOINT: str = Field(
        default="minio:9000",
        validation_alias="MINIO_ENDPOINT",
    )

    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin",
        validation_alias="MINIO_ACCESS_KEY",
    )

    MINIO_SECRET_KEY: str = Field(
        default="minioadmin123",
        validation_alias="MINIO_SECRET_KEY",
    )

    MINIO_BUCKET: str = Field(
        default="auralith",
        validation_alias="MINIO_BUCKET",
    )

    MINIO_SECURE: bool = Field(
        default=False,
        validation_alias="MINIO_SECURE",
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    """
    return Settings()


settings = get_settings()