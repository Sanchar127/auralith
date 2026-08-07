from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.base import Base

# Import all models so Alembic can discover them
import app.db.model  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ---------------------------------------------------------------------
# Configure Alembic to use the synchronous database URL.
# Escape % because ConfigParser treats it as interpolation.
# ---------------------------------------------------------------------

config.set_main_option(
    "sqlalchemy.url",
    settings.ALEMBIC_DATABASE_URL.replace("%", "%%"),
)


def run_migrations_offline() -> None:
    """
    Run migrations without connecting to the database.
    """

    context.configure(
        url=settings.ALEMBIC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations with a live database connection.
    """

    print("=" * 80)
    print("ASYNC URL    :", settings.DATABASE_URL)
    print("ALEMBIC URL  :", settings.ALEMBIC_DATABASE_URL)
    print("=" * 80)

    connectable = create_engine(
        settings.ALEMBIC_DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()