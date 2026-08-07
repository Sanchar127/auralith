from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


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

    # ==========================================================
    # Application
    # ==========================================================

    APP_NAME: str = "Auralith"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ==========================================================
    # PostgreSQL
    # ==========================================================

    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="auralith_subscription")
    POSTGRES_USER: str = Field(default="auralith")
    POSTGRES_PASSWORD: str = Field(default="San6672@@")

    @property
    def DATABASE_URL(self) -> str:
        """
        Async SQLAlchemy URL.
        """

        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    @property
    def ALEMBIC_DATABASE_URL(self) -> str:
        """
        Sync SQLAlchemy URL for Alembic.
        """

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    # ==========================================================
    # JWT
    # ==========================================================

    SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "auralith"
    JWT_AUDIENCE: str = "auralith-api"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ==========================================================
    # Google OAuth
    # ==========================================================

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ==========================================================
    # Redis
    # ==========================================================

    REDIS_URL: str = "redis://redis:6379/0"

    # ==========================================================
    # Celery
    # ==========================================================

    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # ==========================================================
    # Ollama
    # ==========================================================

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # ==========================================================
    # Qdrant
    # ==========================================================

    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "knowledge"
    QDRANT_VECTOR_SIZE: int = 768

    # ==========================================================
    # MinIO
    # ==========================================================

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "auralith"
    MINIO_SECURE: bool = False

    # ==========================================================
    # CORS
    # ==========================================================

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()