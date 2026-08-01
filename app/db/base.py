from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    """

    pass


# ------------------------------------------------------------------
# Import all models so SQLAlchemy registers them with Base.metadata.
# Alembic uses Base.metadata during autogeneration.
# ------------------------------------------------------------------

import app.db.model  # noqa: E402,F401