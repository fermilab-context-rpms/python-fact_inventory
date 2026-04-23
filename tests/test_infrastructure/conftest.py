"""Fixtures for infrastructure-layer tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.infrastructure.db.repositories import FactInventoryRepository

pytest_plugins = [
    "tests.fixtures.app",
]


@pytest.fixture
async def repo(test_db_session: AsyncSession) -> FactInventoryRepository:
    """FactInventoryRepository backed by the per-test database session."""
    return FactInventoryRepository(session=test_db_session)
