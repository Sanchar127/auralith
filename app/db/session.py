from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# ---------------------------------------------------------
# SQLAlchemy Engine
# ---------------------------------------------------------

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)


# ---------------------------------------------------------
# Session Factory
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


# ---------------------------------------------------------
# Dependency
# ---------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency.

    Usage:

        @router.get("/")
        def route(db: Session = Depends(get_db)):
            ...
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()