"""Fixtures for application-layer tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.application.services import FactInventoryService

pytest_plugins = [
    "tests.fixtures.app",
]


@pytest.fixture
async def service(test_db_session: AsyncSession) -> FactInventoryService:
    """FactInventoryService backed by the per-test database session."""
    return FactInventoryService(session=test_db_session)
