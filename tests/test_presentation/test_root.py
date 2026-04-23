"""Tests for GET / root endpoint."""

from litestar.status_codes import HTTP_200_OK, HTTP_405_METHOD_NOT_ALLOWED
from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import get_settings
from tests.support.http import assert_status

ROOT_ENDPOINT = f"{get_settings().app_prefix}/"


async def test_root_endpoint_returns_200(
    test_client: AsyncTestClient,
) -> None:
    """Root endpoint returns HTTP 200."""
    response = await test_client.get(ROOT_ENDPOINT)

    assert_status(response, HTTP_200_OK)
    assert response.json() == {}


async def test_root_endpoint_minimal_body(
    test_client: AsyncTestClient,
) -> None:
    """Root endpoint returns with minimal JSON response (empty object)."""
    response = await test_client.get(ROOT_ENDPOINT)

    assert_status(response, HTTP_200_OK)
    assert response.json() == {}
    assert response.content == b"{}"


async def test_root_endpoint_get_only(
    test_client: AsyncTestClient,
) -> None:
    """Root endpoint only accepts GET requests."""
    response = await test_client.post(ROOT_ENDPOINT, json={})

    assert_status(response, HTTP_405_METHOD_NOT_ALLOWED)
