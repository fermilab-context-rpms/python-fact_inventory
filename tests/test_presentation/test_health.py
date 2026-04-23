"""Tests for GET /health liveness endpoint."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import settings
from tests.support.http import assert_status

API_ROOT = f"{settings.app_prefix}/api"
HEALTH_ENDPOINT = f"{settings.app_prefix}/health"


@pytest.mark.parametrize(
    ("enabled", "expected_status"),
    [
        pytest.param(True, HTTP_200_OK, id="enabled"),
        pytest.param(False, HTTP_404_NOT_FOUND, id="disabled"),
    ],
)
async def test_health_endpoint_availability(
    client_factory,
    *,
    enabled: bool,
    expected_status: int,
) -> None:
    """Health endpoint returns 200 when enabled, 404 when disabled."""
    async with client_factory(
        settings_overrides={"enable_health_endpoint": enabled}
    ) as test_client:
        response = await test_client.get(HEALTH_ENDPOINT)

    assert_status(response, expected_status)
    if enabled:
        assert response.json() is None


async def test_returns_200_with_ok_status(client_with_health: AsyncTestClient) -> None:
    """Health returns 200 with an empty body when enabled."""
    response = await client_with_health.get(HEALTH_ENDPOINT)

    assert_status(response, HTTP_200_OK)
    assert response.json() is None


async def test_independent_of_db_failure(client_with_health: AsyncTestClient) -> None:
    """Health remains up even if database access fails elsewhere."""
    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=Exception("db down"),
    ):
        response = await client_with_health.get(HEALTH_ENDPOINT)

    await asyncio.sleep(0)
    assert_status(response, HTTP_200_OK)


async def test_health_accessible_when_api_router_mounted(
    client_with_health: AsyncTestClient,
) -> None:
    """Health and API routes coexist without interfering with each other."""
    api_response = await client_with_health.get(API_ROOT)
    health_response = await client_with_health.get(HEALTH_ENDPOINT)

    assert_status(api_response, HTTP_200_OK)
    assert_status(health_response, HTTP_200_OK)


async def test_accessible_when_ready_disabled(
    client_with_health: AsyncTestClient,
) -> None:
    """Health availability is independent of the ready endpoint."""
    response = await client_with_health.get(HEALTH_ENDPOINT)

    assert_status(response, HTTP_200_OK)


async def test_post_not_allowed(client_with_health: AsyncTestClient) -> None:
    """Health only accepts GET."""
    response = await client_with_health.post(HEALTH_ENDPOINT, json={})

    assert_status(response, HTTP_405_METHOD_NOT_ALLOWED)
