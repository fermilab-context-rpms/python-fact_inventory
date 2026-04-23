"""Database migration utilities and checks.

Ensures database schema is up to date with migration definitions.
"""

import logging
import os
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from fact_inventory.lib.exceptions import MigrationNotUpToDateError

logger = logging.getLogger(__name__)

#: Environment variable that overrides the migrations directory location.
#: When unset, the ``migrations/`` directory shipped alongside the installed
#: ``fact_inventory`` package is used, so the check works both from a source
#: checkout and from an installed deployment.
MIGRATIONS_DIR_ENV_VAR = "FACT_INVENTORY_MIGRATIONS_DIR"


def _migrations_dir() -> str:
    """Return the directory containing Alembic revision scripts.

    Prefers the ``FACT_INVENTORY_MIGRATIONS_DIR`` environment variable so
    deployments can point at an explicit location. Otherwise resolves the
    ``migrations/`` directory relative to the installed package, which works
    in both source checkouts and installed packages.

    Returns
    -------
    str
        Absolute path to the directory holding Alembic revision scripts.
    """
    override = os.environ.get(MIGRATIONS_DIR_ENV_VAR)
    if override:
        return override
    return str(Path(__file__).resolve().parents[3] / "migrations")


async def get_database_revision(
    database_uri: str | None = None,
    *,
    engine: AsyncEngine | None = None,
) -> str | None:
    """Get the current migration revision from the database.

    Parameters
    ----------
    database_uri : str | None
        SQLAlchemy async database URI used when ``engine`` is not supplied.
    engine : AsyncEngine | None
        Existing application engine to use for the check. The caller retains
        ownership of this engine.

    Returns
    -------
    str | None
        Current revision version, or None if alembic_version table doesn't exist.
    """
    owns_engine = engine is None
    if engine is None:
        if database_uri is None:
            raise ValueError("database_uri or engine is required")  # noqa: TRY003
        engine = create_async_engine(database_uri, echo=False)
    try:
        async with engine.begin() as conn:
            # Check if alembic_version table exists.
            # Combine inspect() and get_table_names() in one run_sync call so
            # both use the same synchronous connection and no outer reference
            # to the inspector escapes the sync context.
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )

            if "alembic_version" not in tables:
                return None

            # Get the current revision. With multiple Alembic heads the table
            # can hold several rows; select all and report the lexicographically
            # last so the result is deterministic regardless of row order.
            result = await conn.run_sync(
                lambda c: c.execute(
                    text("SELECT version_num FROM alembic_version ORDER BY version_num")
                )
            )
            row = result.fetchone()
            if row:
                return str(row[0])
            return None
    finally:
        if owns_engine:
            await engine.dispose()


def get_head_revision() -> str:
    """Get the latest migration revision from the migrations directory.

    Returns
    -------
    str
        Head revision version.

    Raises
    ------
    RuntimeError
        If no migrations are found.
    """
    script_dir = ScriptDirectory(dir=_migrations_dir())
    head = script_dir.get_current_head()

    if not head:
        msg = "No migrations found in migrations/ directory"
        raise RuntimeError(msg)

    return head


async def check_migrations_up_to_date(
    database_uri: str | None = None,
    *,
    engine: AsyncEngine | None = None,
) -> None:
    """Check that database migrations are up to date.

    Parameters
    ----------
    database_uri : str | None
        SQLAlchemy async database URI used when ``engine`` is not supplied.
    engine : AsyncEngine | None
        Existing application engine to use for the check. The caller retains
        ownership of this engine.

    Raises
    ------
    MigrationNotUpToDateError
        If database revision doesn't match head revision.
    """
    current_revision = await get_database_revision(database_uri, engine=engine)
    head_revision = get_head_revision()

    if current_revision != head_revision:
        raise MigrationNotUpToDateError(current_revision, head_revision)

    logger.info("Database migrations up to date (revision: %s)", head_revision)
