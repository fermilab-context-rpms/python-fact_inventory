"""Shared HTTP helpers for presentation and integration tests."""

from typing import Any

from litestar.testing import AsyncTestClient

from fact_inventory.lib.settings import get_settings
from tests.factories import create_minimal

__all__ = [
    "FACTS_ENDPOINT",
    "assert_status",
    "post_facts",
    "request_id_headers",
]
FACTS_ENDPOINT = f"{get_settings().app_prefix}/api/v1/facts"


def request_id_headers(request_id: str | None) -> dict[str, str] | None:
    """Return headers for a request ID when one is supplied."""
    if request_id is None:
        return None
    return {"X-Request-ID": request_id}


def assert_status(response: Any, expected_status: int) -> None:
    """Assert that response has the expected HTTP status code."""
    assert response.status_code == expected_status


async def post_facts(
    client: AsyncTestClient,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
) -> Any:
    """POST to the facts endpoint using either JSON or raw content."""
    if payload is None and content is None:
        payload = create_minimal()

    kwargs: dict[str, Any] = {}
    if payload is not None:
        kwargs["json"] = payload
    if content is not None:
        kwargs["content"] = content
    if headers is not None:
        kwargs["headers"] = headers

    return await client.post(FACTS_ENDPOINT, **kwargs)
