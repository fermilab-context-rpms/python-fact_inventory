import asyncio
import os
from typing import TYPE_CHECKING, cast

from alembic import context
from alembic.autogenerate import rewriter
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

from fact_inventory.infrastructure.db.models import UUIDAuditBase

if TYPE_CHECKING:
    from advanced_alchemy.alembic.commands import AlembicCommandConfig
    from sqlalchemy.engine import Connection

__all__ = ("do_run_migrations", "run_migrations_offline", "run_migrations_online")

target_metadata = UUIDAuditBase.metadata


# this is the Alembic Config object, which provides
# access to the values within the pyproject.toml file.
config: "AlembicCommandConfig" = context.config  # type: ignore
writer = rewriter.Rewriter()


def _get_db_url() -> str:
    """Get database URL from advanced_alchemy config or environment.

    Tries to use config.db_url if available (when called by advanced_alchemy),
    falls back to environment variable, then falls back to pyproject.toml config.
    """
    if hasattr(config, "db_url") and config.db_url:
        return config.db_url

    if "DATABASE_URI" in os.environ:
        return os.environ["DATABASE_URI"]

    db_url = config.get_main_option("sqlalchemy.url")
    if not db_url:
        msg = (
            "No database URL found. Set DATABASE_URI env var or "
            "sqlalchemy.url in pyproject.toml"
        )
        raise RuntimeError(msg)
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=_get_db_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=writer,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: "Connection") -> None:
    """Run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=writer,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.

    Raises:
        RuntimeError: If the engine cannot be created from the config.
    """
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_db_url()

    connectable = cast(
        "AsyncEngine",
        getattr(config, "engine", None)
        or async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        ),
    )
    if connectable is None:  # pyright: ignore[reportUnnecessaryComparison]
        msg = "Could not get engine from config. Please ensure pyproject.toml [tool.alembic] is properly configured."  # noqa: E501
        raise RuntimeError(
            msg,
        )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
