"""Tests for GET /metrics Prometheus endpoint."""

import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import get_settings
from tests.support.http import assert_status

API_ROOT = f"{get_settings().app_prefix}/api"
HEALTH_ENDPOINT = f"{get_settings().app_prefix}/health"
METRICS_ENDPOINT = f"{get_settings().app_prefix}/metrics"
READY_ENDPOINT = f"{get_settings().app_prefix}/ready"


@pytest.mark.parametrize(
    ("enabled", "expected_status"),
    [
        pytest.param(True, HTTP_200_OK, id="enabled"),
        pytest.param(False, HTTP_404_NOT_FOUND, id="disabled"),
    ],
)
async def test_metrics_endpoint_availability(
    client_factory,
    *,
    enabled: bool,
    expected_status: int,
) -> None:
    """Metrics endpoint returns 200 when enabled, 404 when disabled."""
    async with client_factory(
        settings_overrides={"enable_metrics": enabled}
    ) as test_client:
        response = await test_client.get(METRICS_ENDPOINT)

    assert_status(response, expected_status)


async def test_post_not_allowed(client_with_metrics: AsyncTestClient) -> None:
    """Metrics only accepts GET."""
    response = await client_with_metrics.post(METRICS_ENDPOINT, json={})

    assert_status(response, HTTP_405_METHOD_NOT_ALLOWED)


async def test_api_router_still_works_when_metrics_disabled(
    test_client: AsyncTestClient,
) -> None:
    """Disabling metrics does not affect the API router."""
    response = await test_client.get(API_ROOT)

    assert_status(response, HTTP_200_OK)


async def test_health_unaffected_when_metrics_enabled(
    client_with_metrics: AsyncTestClient,
) -> None:
    """Enabling metrics does not implicitly enable health."""
    response = await client_with_metrics.get(HEALTH_ENDPOINT)

    assert_status(response, HTTP_404_NOT_FOUND)


async def test_ready_unaffected_when_metrics_enabled(
    client_with_metrics: AsyncTestClient,
) -> None:
    """Enabling metrics does not implicitly enable ready."""
    response = await client_with_metrics.get(READY_ENDPOINT)

    assert_status(response, HTTP_404_NOT_FOUND)
