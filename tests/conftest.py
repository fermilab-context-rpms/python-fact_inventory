"""Pytest configuration for fact_inventory test suite.

Sets up test environment, database, and migrations. App fixtures are scoped
to DB/HTTP-facing subdirectories (test_application/, test_infrastructure/,
test_integration/, test_presentation/) so pure unit tests (test_domain/,
test_config/) avoid the overhead of booting the application.
"""

import os

import pytest

# DEPLOYMENT=testing must be set BEFORE any app imports since pydantic-settings
# loads environment at import time.
os.environ.setdefault("DEPLOYMENT", "testing")

# Configure test database BEFORE importing app modules.
# This cannot be in pyproject.toml since pytest doesn't support setting
# arbitrary environment variables.
from tests.support.migrations import TestDatabaseSetup, run_migrations

_db_setup = TestDatabaseSetup()
_db_setup.setup()

# Env and database setup, now safe to import app modules


@pytest.fixture(scope="session", autouse=True)
def run_migrations_for_tests() -> None:
    """Run Alembic migrations just once per test session.

    Ensures tests use the same migration path as production code,
    verifying that migrations actually work.
    """
    _db_setup.cleanup_db_file()
    run_migrations()
