"""Database migration utilities and checks.

Ensures database schema is up to date with migration definitions.
"""

import logging
from pathlib import Path
from typing import cast

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from fact_inventory.lib.exceptions import MigrationNotUpToDateError


async def get_database_revision(database_uri: str) -> str | None:
    """Get the current migration revision from the database.

    Parameters
    ----------
    database_uri : str
        SQLAlchemy async database URI.

    Returns
    -------
    str | None
        Current revision version, or None if alembic_version table doesn't exist.
    """
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

            # Get the current revision
            result = await conn.run_sync(
                lambda c: c.execute(text("SELECT version_num FROM alembic_version"))
            )
            row = result.fetchone()
            if row:
                return cast("str", row[0])
            return None
    finally:
        await engine.dispose()


def get_head_revision() -> str:
    """Get the latest migration revision from migrations/ directory.

    Returns
    -------
    str
        Head revision version.

    Raises
    ------
    RuntimeError
        If no migrations are found.
    """
    pyproject_path = Path(__file__).parents[3] / "pyproject.toml"
    alembic_cfg = AlembicConfig(toml_file=str(pyproject_path))

    # Get the script directory
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    head = script_dir.get_current_head()

    if not head:
        msg = "No migrations found in migrations/ directory"
        raise RuntimeError(msg)

    return head


async def check_migrations_up_to_date(database_uri: str) -> None:
    """Check that database migrations are up to date.

    Parameters
    ----------
    database_uri : str
        SQLAlchemy async database URI.

    Raises
    ------
    MigrationNotUpToDateError
        If database revision doesn't match head revision.
    """
    current_revision = await get_database_revision(database_uri)
    head_revision = get_head_revision()

    if current_revision != head_revision:
        raise MigrationNotUpToDateError(current_revision, head_revision)

    logging.getLogger(__name__).info(
        "Database migrations up to date (revision: %s)", head_revision
    )
