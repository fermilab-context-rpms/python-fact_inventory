"""Tests for GET /ready readiness endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_503_SERVICE_UNAVAILABLE,
)
from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import get_settings
from tests.support.http import assert_status

API_ROOT = f"{get_settings().app_prefix}/api"
HEALTH_ENDPOINT = f"{get_settings().app_prefix}/health"
READY_ENDPOINT = f"{get_settings().app_prefix}/ready"


@pytest.mark.parametrize(
    ("enabled", "expected_status"),
    [
        pytest.param(True, HTTP_200_OK, id="enabled"),
        pytest.param(False, HTTP_404_NOT_FOUND, id="disabled"),
    ],
)
async def test_ready_endpoint_availability(
    client_factory,
    *,
    enabled: bool,
    expected_status: int,
) -> None:
    """Ready endpoint returns 200 when enabled, 404 when disabled."""
    async with client_factory(
        settings_overrides={"enable_ready_endpoint": enabled}
    ) as test_client:
        response = await test_client.get(READY_ENDPOINT)

    assert_status(response, expected_status)
    if enabled:
        assert response.json() == {"status": "ready"}


async def test_post_not_allowed(client_with_ready: AsyncTestClient) -> None:
    """Ready only accepts GET."""
    response = await client_with_ready.post(READY_ENDPOINT, json={})

    assert_status(response, HTTP_405_METHOD_NOT_ALLOWED)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(Exception("db down"), id="db-error"),
        pytest.param(TimeoutError("timeout"), id="timeout"),
    ],
)
async def test_ready_returns_503_when_dependency_check_fails(
    client_with_ready: AsyncTestClient,
    error: Exception,
) -> None:
    """Ready reports dependency failures as 503."""
    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=error,
    ):
        response = await client_with_ready.get(READY_ENDPOINT)

    assert_status(response, HTTP_503_SERVICE_UNAVAILABLE)
    assert "detail" in response.json()


async def test_ready_logs_dependency_failure(
    client_with_ready: AsyncTestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Readiness failures are logged without exposing infrastructure details."""
    error = RuntimeError("secret database connection detail")
    with (
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            side_effect=error,
        ),
        caplog.at_level("ERROR", logger="fact_inventory.presentation.ready"),
    ):
        response = await client_with_ready.get(READY_ENDPOINT)

    assert_status(response, HTTP_503_SERVICE_UNAVAILABLE)
    assert "Readiness database check failed" in caplog.text
    assert "secret database connection detail" not in response.text


async def test_health_still_ok_when_ready_fails(
    client_with_health_and_ready: AsyncTestClient,
) -> None:
    """Health can succeed while ready fails."""
    with patch(
        "sqlalchemy.ext.asyncio.AsyncSession.execute",
        new_callable=AsyncMock,
        side_effect=Exception("db down"),
    ):
        health_response = await client_with_health_and_ready.get(HEALTH_ENDPOINT)
        ready_response = await client_with_health_and_ready.get(READY_ENDPOINT)

    assert_status(health_response, HTTP_200_OK)
    assert_status(ready_response, HTTP_503_SERVICE_UNAVAILABLE)


async def test_ready_works_when_api_router_mounted(
    client_with_ready: AsyncTestClient,
) -> None:
    """Ready and API endpoints coexist without interference."""
    api_response = await client_with_ready.get(API_ROOT)
    ready_response = await client_with_ready.get(READY_ENDPOINT)

    assert_status(api_response, HTTP_200_OK)
    assert_status(ready_response, HTTP_200_OK)


async def test_api_router_still_works_when_ready_disabled(
    test_client: AsyncTestClient,
) -> None:
    """Disabling ready does not affect the API router."""
    response = await test_client.get(API_ROOT)

    assert_status(response, HTTP_200_OK)
