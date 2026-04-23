"""Tests for the traceparent-stamping ASGI middleware.

Design Notes:
- Unit tests exercise TraceparentMiddleware.handle() directly against a
  fake ASGI ``next_app``/``send`` pair, mocking get_traceparent_header to
  avoid depending on an active OTEL span (mirrors tests/test_lib/test_otel.py).
- Integration-level confirmation that real clients receive the header on
  real success/error responses lives in tests/test_integration/test_app.py.
"""

from typing import Any
from unittest.mock import patch

import pytest
from litestar.enums import ScopeType

from fact_inventory.server.middleware.traceparent import TraceparentMiddleware

FAKE_TRACEPARENT = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"


def build_scope(scope_type: str = "http") -> dict[str, Any]:
    """Build a minimal ASGI scope of the given type."""
    return {"type": scope_type}


async def noop_receive() -> dict[str, Any]:
    """Return a minimal ASGI receive event."""
    return {"type": "http.request"}


def make_next_app(
    messages: list[dict[str, Any]],
) -> Any:
    """Return a fake ASGI app that sends the given messages via its send callable."""

    async def next_app(scope: Any, receive: Any, send: Any) -> None:
        for message in messages:
            await send(message)

    return next_app


async def test_handle_adds_traceparent_header_to_response_start() -> None:
    """The middleware injects a traceparent header into http.response.start."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    next_app = make_next_app(
        [
            {"type": "http.response.start", "status": 200, "headers": []},
            {"type": "http.response.body", "body": b"", "more_body": False},
        ]
    )

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        middleware = TraceparentMiddleware()
        await middleware.handle(build_scope(), noop_receive, send, next_app)

    start_message = sent[0]
    headers = dict(start_message["headers"])
    assert headers[b"traceparent"] == FAKE_TRACEPARENT.encode()


async def test_handle_overwrites_existing_traceparent_header() -> None:
    """A pre-existing traceparent header is replaced, not duplicated."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    next_app = make_next_app(
        [
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"traceparent", b"stale-value")],
            },
        ]
    )

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        middleware = TraceparentMiddleware()
        await middleware.handle(build_scope(), noop_receive, send, next_app)

    headers = sent[0]["headers"]
    traceparent_headers = [h for h in headers if h[0] == b"traceparent"]
    assert len(traceparent_headers) == 1
    assert traceparent_headers[0][1] == FAKE_TRACEPARENT.encode()


async def test_handle_preserves_other_headers() -> None:
    """Existing non-traceparent headers are preserved untouched."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    next_app = make_next_app(
        [
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            },
        ]
    )

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        middleware = TraceparentMiddleware()
        await middleware.handle(build_scope(), noop_receive, send, next_app)

    headers = dict(sent[0]["headers"])
    assert headers[b"content-type"] == b"application/json"
    assert headers[b"traceparent"] == FAKE_TRACEPARENT.encode()


async def test_handle_passes_through_non_start_messages_unmodified() -> None:
    """Messages other than http.response.start are forwarded unchanged."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    body_message = {"type": "http.response.body", "body": b"hello", "more_body": False}
    next_app = make_next_app([body_message])

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        middleware = TraceparentMiddleware()
        await middleware.handle(build_scope(), noop_receive, send, next_app)

    assert sent == [body_message]


async def test_handle_calls_get_traceparent_header_for_error_responses_too() -> None:
    """The header is stamped regardless of the response status code."""
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    next_app = make_next_app(
        [
            {"type": "http.response.start", "status": 500, "headers": []},
        ]
    )

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        middleware = TraceparentMiddleware()
        await middleware.handle(build_scope(), noop_receive, send, next_app)

    headers = dict(sent[0]["headers"])
    assert headers[b"traceparent"] == FAKE_TRACEPARENT.encode()


def test_middleware_scopes_are_http_only() -> None:
    """The middleware is configured to only apply to HTTP scopes."""
    assert TraceparentMiddleware.scopes == (ScopeType.HTTP,)


@pytest.mark.parametrize(
    "scope_type",
    ["websocket", "lifespan"],
)
async def test_non_http_scopes_bypass_middleware_via_call(scope_type: str) -> None:
    """Non-HTTP scopes bypass handle() entirely via the base __call__ dispatch."""
    sent: list[dict[str, Any]] = []
    called_next_app = False

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    async def next_app(scope: Any, receive: Any, send: Any) -> None:
        nonlocal called_next_app
        called_next_app = True

    middleware = TraceparentMiddleware()
    asgi_callable = middleware(next_app)

    with patch(
        "fact_inventory.server.middleware.traceparent.get_traceparent_header",
        return_value=FAKE_TRACEPARENT,
    ):
        await asgi_callable(build_scope(scope_type), noop_receive, send)

    assert called_next_app is True
    assert sent == []
