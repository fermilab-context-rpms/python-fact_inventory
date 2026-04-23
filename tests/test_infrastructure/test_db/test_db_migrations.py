"""Tests for database migration checks.

Tests verify migration detection, database revision tracking, and migration
status validation. These are critical for production deployments: applications
must refuse to start if database schema is out of sync.

Design Notes:
- Head revision is read dynamically from migration files (not hardcoded)
  This ensures tests auto-update as migrations are added
- Database revision is queried from actual alembic_version table
- Test paths use temp SQLite files for isolation
- Errors include both current and expected revisions for troubleshooting
"""

from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from fact_inventory.infrastructure.db.db_migrations import (
    check_migrations_up_to_date,
    get_database_revision,
    get_head_revision,
)
from fact_inventory.lib.exceptions import MigrationNotUpToDateError

ALEMBIC_VERSION_TABLE_DDL = (
    "CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
)

ALEMBIC_VERSION_INSERT_SQL = "INSERT INTO alembic_version (version_num) VALUES (?)"


def sqlite_db_uri(tmp_path: Path) -> str:
    """Return an isolated SQLite URI for a temp test database."""
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


async def setup_migration_table(db_uri: str, version: str) -> None:
    """Helper to set up alembic_version table with a specific version."""
    engine = create_async_engine(db_uri)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute(text(ALEMBIC_VERSION_TABLE_DDL)))
        await conn.run_sync(
            lambda c: c.execute(
                text(ALEMBIC_VERSION_INSERT_SQL.replace("?", ":version")),
                {"version": version},
            )
        )
    await engine.dispose()


def test_get_head_revision_returns_head_revision() -> None:
    """Head revision is non-empty and stable across multiple calls."""
    head = get_head_revision()
    assert len(head) > 0, "Head revision must not be empty"
    # Verify it's stable - calling again returns same value
    assert get_head_revision() == head, (
        "Head revision must be stable across multiple calls"
    )


def test_get_head_revision_raises_when_no_migrations_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raises RuntimeError when no migrations are found."""

    # Mock ScriptDirectory to return None for head
    def mock_get_current_head(_: ScriptDirectory) -> None:
        return None

    monkeypatch.setattr(ScriptDirectory, "get_current_head", mock_get_current_head)

    with pytest.raises(RuntimeError):
        get_head_revision()


async def test_get_database_revision_returns_none_when_no_migrations_applied(
    tmp_path: Path,
) -> None:
    """Returns None when alembic_version table doesn't exist."""
    db_uri = sqlite_db_uri(tmp_path)

    revision = await get_database_revision(db_uri)
    assert revision is None


async def test_get_database_revision_returns_revision_when_migration_applied(
    tmp_path: Path,
) -> None:
    """Returns the revision from alembic_version table."""
    db_uri = sqlite_db_uri(tmp_path)

    await setup_migration_table(db_uri, "abc123")
    revision = await get_database_revision(db_uri)
    assert revision == "abc123"


async def test_check_migrations_up_to_date_raises_when_no_migrations_applied(
    tmp_path: Path,
) -> None:
    """Raises MigrationNotUpToDateError when no migrations applied."""
    db_uri = sqlite_db_uri(tmp_path)

    with pytest.raises(MigrationNotUpToDateError) as exc_info:
        await check_migrations_up_to_date(db_uri)

    error = exc_info.value
    assert error.current_revision is None
    assert error.head_revision == get_head_revision()


async def test_check_migrations_up_to_date_raises_when_migrations_behind(
    tmp_path: Path,
) -> None:
    """Raises MigrationNotUpToDateError when db revision is behind head."""
    db_uri = sqlite_db_uri(tmp_path)

    await setup_migration_table(db_uri, "old_rev")

    with pytest.raises(MigrationNotUpToDateError) as exc_info:
        await check_migrations_up_to_date(db_uri)

    error = exc_info.value
    assert error.current_revision == "old_rev"
    # Verify head_revision matches actual migrations (not hardcoded)
    assert error.head_revision == get_head_revision()


async def test_check_migrations_up_to_date_passes_when_migrations_up_to_date(
    tmp_path: Path,
) -> None:
    """Passes when database revision matches head."""
    db_uri = sqlite_db_uri(tmp_path)

    # Use dynamic head revision so this test doesn't need updates as migrations are added
    head_revision = get_head_revision()
    await setup_migration_table(db_uri, head_revision)

    # Should not raise
    await check_migrations_up_to_date(db_uri)


async def test_get_database_revision_returns_none_when_migration_table_is_empty(
    tmp_path: Path,
) -> None:
    """Returns None when alembic_version table exists but is empty."""
    db_uri = sqlite_db_uri(tmp_path)

    # Setup database with empty alembic_version table
    engine = create_async_engine(db_uri)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: c.execute(text(ALEMBIC_VERSION_TABLE_DDL)))
    await engine.dispose()

    revision = await get_database_revision(db_uri)
    assert revision is None
