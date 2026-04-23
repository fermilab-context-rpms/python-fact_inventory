"""Tests for OpenTelemetry trace context management.

Tests verify trace ID and span ID extraction with proper formatting and
fallback handling for missing/invalid contexts. These functions are critical
for linking logs to distributed traces in observability systems.

Design Notes:
- Always use mocks to avoid depending on active OTEL spans
- Test both valid and invalid contexts (None, 0)
- Verify hex formatting is lowercase per OTEL spec
- Verify fallback behavior returns zero-padded strings
"""

from unittest.mock import MagicMock, patch

import pytest

from fact_inventory.lib.otel import get_span_id, get_trace_id, get_traceparent_header


def build_span(
    *,
    trace_id: int | None = None,
    span_id: int | None = None,
    has_context: bool = True,
) -> tuple[MagicMock, MagicMock | None]:
    """Build mock spans with explicit trace/span identifiers."""
    mock_span = MagicMock()
    mock_ctx = MagicMock(trace_id=trace_id, span_id=span_id) if has_context else None
    mock_span.get_span_context.return_value = mock_ctx
    return mock_span, mock_ctx


def test_get_trace_id_returns_valid_trace_id_when_span_exists() -> None:
    """Valid trace ID formatted as 32-char lowercase hex when context exists."""
    mock_span, mock_ctx = build_span(trace_id=12345678901234567890123456789012)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        trace_id = get_trace_id()

    assert len(trace_id) == 32
    assert trace_id == format(mock_ctx.trace_id, "032x")


@pytest.mark.parametrize("trace_id_value", [None, 0])
def test_get_trace_id_returns_zero_for_invalid_values(
    trace_id_value: int | None,
) -> None:
    """Trace ID defaults to zeros when trace_id is None or 0."""
    mock_span, _ = build_span(trace_id=trace_id_value)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        trace_id = get_trace_id()

    assert trace_id == "0" * 32


def test_get_trace_id_returns_zero_when_no_span_context() -> None:
    """Trace ID defaults to zeros when span context is None."""
    mock_span, _ = build_span(has_context=False)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        trace_id = get_trace_id()

    assert trace_id == "0" * 32


def test_get_trace_id_format_is_lowercase_hex() -> None:
    """Trace ID formatted as lowercase hexadecimal."""
    mock_span, _ = build_span(trace_id=0xDEADBEEF00000000123456789ABCDEF0)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        trace_id = get_trace_id()

    assert trace_id == trace_id.lower()
    for c in trace_id:
        assert c in "0123456789abcdef"


def test_get_span_id_returns_valid_span_id_when_span_exists() -> None:
    """Valid span ID formatted as 16-char lowercase hex when context exists."""
    mock_span, mock_ctx = build_span(span_id=9876543210987654)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        span_id = get_span_id()

    assert len(span_id) == 16
    assert span_id == format(mock_ctx.span_id, "016x")


@pytest.mark.parametrize("span_id_value", [None, 0])
def test_get_span_id_returns_zero_for_invalid_values(
    span_id_value: int | None,
) -> None:
    """Span ID defaults to zeros when span_id is None or 0."""
    mock_span, _ = build_span(span_id=span_id_value)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        span_id = get_span_id()

    assert span_id == "0" * 16


def test_get_span_id_returns_zero_when_no_span_context() -> None:
    """Span ID defaults to zeros when span context is None."""
    mock_span, _ = build_span(has_context=False)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        span_id = get_span_id()

    assert span_id == "0" * 16


def test_get_span_id_format_is_lowercase_hex() -> None:
    """Span ID formatted as lowercase hexadecimal."""
    mock_span, _ = build_span(span_id=0xDEADBEEF00000000)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        span_id = get_span_id()

    assert span_id == span_id.lower()
    for c in span_id:
        assert c in "0123456789abcdef"


def test_get_traceparent_header_returns_valid_format_with_valid_context() -> None:
    """Valid traceparent header in W3C format with valid trace/span context."""
    trace_id_val = 0xDEADBEEF00000000123456789ABCDEF0
    span_id_val = 0xFEDCBA9876543210

    mock_span, _ = build_span(trace_id=trace_id_val, span_id=span_id_val)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    # W3C Trace Context format: "00-{trace_id}-{span_id}-01"
    assert header.startswith("00-")
    assert header.endswith("-01")
    parts = header.split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert parts[3] == "01"
    # Trace ID and span ID should be hex
    assert len(parts[1]) == 32
    assert len(parts[2]) == 16
    for c in parts[1] + parts[2]:
        assert c in "0123456789abcdef"


def test_get_traceparent_header_uses_lowercase_hex() -> None:
    """Traceparent header components use lowercase hexadecimal."""
    mock_span, _ = build_span(
        trace_id=0xDEADBEEF00000000123456789ABCDEF0,
        span_id=0xFEDCBA9876543210,
    )

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    # Entire header (except dashes) should be lowercase
    header_no_dashes = header.replace("-", "")
    assert header_no_dashes == header_no_dashes.lower()


def test_get_traceparent_header_handles_missing_span_context() -> None:
    """Traceparent header valid even with missing span context."""
    mock_span, _ = build_span(has_context=False)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    # Should still be valid W3C format with zeros
    assert header == "00-" + "0" * 32 + "-" + "0" * 16 + "-01"


def test_get_traceparent_header_handles_zero_trace_id() -> None:
    """Traceparent header valid when trace_id is zero."""
    mock_span, _ = build_span(trace_id=0, span_id=12345)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    # Trace ID portion should be all zeros
    parts = header.split("-")
    assert parts[1] == "0" * 32


def test_get_traceparent_header_handles_zero_span_id() -> None:
    """Traceparent header valid when span_id is zero."""
    mock_span, _ = build_span(trace_id=12345, span_id=0)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    # Span ID portion should be all zeros
    parts = header.split("-")
    assert parts[2] == "0" * 16


def test_get_traceparent_header_none_trace_id() -> None:
    """Traceparent header valid when trace_id is None."""
    mock_span, _ = build_span(trace_id=None, span_id=54321)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    parts = header.split("-")
    assert parts[1] == "0" * 32


def test_get_traceparent_header_none_span_id() -> None:
    """Traceparent header valid when span_id is None."""
    mock_span, _ = build_span(trace_id=54321, span_id=None)

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        header = get_traceparent_header()

    parts = header.split("-")
    assert parts[2] == "0" * 16
