"""Tests for the top-level presentation router."""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import get_settings
from fact_inventory.presentation.router import create_router
from tests.support.http import assert_status, post_facts

API_ROOT = f"{get_settings().app_prefix}/api"

HEALTH_ENDPOINT = f"{get_settings().app_prefix}/health"
READY_ENDPOINT = f"{get_settings().app_prefix}/ready"


async def test_health_at_root(client_with_health: AsyncTestClient) -> None:
    """Health is mounted at the top level when enabled."""
    response = await client_with_health.get(HEALTH_ENDPOINT)

    assert_status(response, HTTP_200_OK)


async def test_ready_at_root(client_with_ready: AsyncTestClient) -> None:
    """Ready is mounted at the top level when enabled."""
    response = await client_with_ready.get(READY_ENDPOINT)

    assert_status(response, HTTP_200_OK)


async def test_api_mounted_at_api_prefix(test_client: AsyncTestClient) -> None:
    """The facts endpoint is reachable under the API prefix."""
    response = await post_facts(test_client)

    assert_status(response, HTTP_201_CREATED)


async def test_api_root_returns_200(test_client: AsyncTestClient) -> None:
    """The API root responds with the application marker."""
    response = await test_client.get(API_ROOT)

    assert_status(response, HTTP_200_OK)
    assert response.json() == {"app": "fact_inventory"}


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"{API_ROOT}/health", id="health-under-api"),
        pytest.param(f"{API_ROOT}/ready", id="ready-under-api"),
        pytest.param("/v1/facts", id="v1-at-root"),
    ],
)
async def test_endpoints_not_accessible_at_wrong_paths(
    test_client: AsyncTestClient,
    path: str,
) -> None:
    """Endpoints are not accessible outside their configured paths."""
    if "v1/facts" in path:
        response = await test_client.post(path, json={})
    else:
        response = await test_client.get(path)

    assert_status(response, HTTP_404_NOT_FOUND)


@pytest.mark.parametrize(
    ("enabled_endpoint", "endpoint_path"),
    [
        pytest.param("health", HEALTH_ENDPOINT, id="custom-health-disabled"),
        pytest.param("ready", READY_ENDPOINT, id="custom-ready-disabled"),
    ],
)
async def test_custom_router_path_endpoints_disabled(
    client_with_custom_router_path: AsyncTestClient,
    enabled_endpoint: str,
    endpoint_path: str,
) -> None:
    """Custom router apps do not enable health/ready by default."""
    response = await client_with_custom_router_path.get(endpoint_path)

    assert_status(response, HTTP_404_NOT_FOUND)


async def test_custom_router_path_api(
    client_with_custom_router_path: AsyncTestClient,
) -> None:
    """The facts endpoint still works under the custom router app."""
    response = await post_facts(client_with_custom_router_path)

    assert_status(response, HTTP_201_CREATED)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"{API_ROOT}/health", id="health-not-under-custom-api"),
        pytest.param("/facts", id="v1-not-at-root-in-custom-app"),
    ],
)
async def test_custom_router_path_endpoints_not_at_wrong_paths(
    client_with_custom_router_path: AsyncTestClient,
    path: str,
) -> None:
    """Endpoints stay outside the API subtree on custom router apps."""
    response = await client_with_custom_router_path.get(path)

    assert_status(response, HTTP_404_NOT_FOUND)


def _route_paths(router_path: str = "/", **overrides: object) -> set[str]:
    settings = get_settings().model_copy(update=overrides) if overrides else None
    return {
        route.path
        for route in create_router(path=router_path, settings=settings).routes
    }


def test_create_router_without_settings_registers_optional_probes() -> None:
    """Calling create_router() with no settings still resolves settings.

    Health/ready probes are governed by the resolved settings; the testing
    deployment enables neither, so only the root and API routes mount.
    """
    paths = _route_paths()
    assert "/" in paths
    assert "/health" not in paths
    assert "/ready" not in paths


def test_create_router_with_probes_enabled_registers_probes() -> None:
    """Probes are registered when the resolved settings enable them."""
    paths = _route_paths(enable_health_endpoint=True, enable_ready_endpoint=True)
    assert {"/", "/health", "/ready"} <= paths
