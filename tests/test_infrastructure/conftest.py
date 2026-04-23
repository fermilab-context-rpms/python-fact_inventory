"""Fixtures for infrastructure-layer tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.infrastructure.db.repositories import (
    BackgroundJobLockRepository,
    FactInventoryRepository,
)
from tests.support.db import truncate_background_job_lock

pytest_plugins = [
    "tests.fixtures.app",
]


@pytest.fixture
async def repo(test_db_session: AsyncSession) -> FactInventoryRepository:
    """FactInventoryRepository backed by the per-test database session."""
    return FactInventoryRepository(session=test_db_session)


@pytest.fixture
async def lock_repo(test_db_session: AsyncSession) -> BackgroundJobLockRepository:
    """BackgroundJobLockRepository backed by the per-test database session.

    The background_job_lock table is truncated before and after each test to
    keep lock tests isolated.
    """
    await truncate_background_job_lock(test_db_session)
    yield BackgroundJobLockRepository(session=test_db_session)
    await truncate_background_job_lock(test_db_session)
