"""Request context management for observability.

Provides access to OpenTelemetry trace context for distributed tracing.
Integrates with Litestar's OpenTelemetry middleware to automatically track
trace_id across async execution.
"""

from opentelemetry import trace

__all__ = ["get_span_id", "get_trace_id", "get_traceparent_header"]


def get_span_id() -> str:
    """Get the current OpenTelemetry span ID from the active span context.

    Returns
    -------
    str
        The hex string span_id from the current span context, or "0" * 16 if no
        span context is available (e.g., before OTEL middleware processing).

    Notes
    -----
    This function extracts the span_id from OpenTelemetry's automatic span context.
    The span is created by Litestar's OpenTelemetryConfig middleware and is
    automatically propagated through async contexts.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.span_id:
        return format(ctx.span_id, "016x")
    return "0" * 16


def get_trace_id() -> str:
    """Get the current OpenTelemetry trace ID from the active span context.

    Returns
    -------
    str
        The hex string trace_id from the current span context, or "0" * 32 if no
        span context is available (e.g., before OTEL middleware processing).

    Notes
    -----
    This function extracts the trace_id from OpenTelemetry's automatic span context.
    The span is created by Litestar's OpenTelemetryConfig middleware and is
    automatically propagated through async contexts.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return "0" * 32


def get_traceparent_header() -> str:
    """Generate W3C Trace Context traceparent header value.

    Returns
    -------
    str
        A valid W3C Trace Context traceparent header value in format:
        "00-{trace_id}-{span_id}-01"

        Where:
        - 00 = version (always 0, per W3C spec)
        - {trace_id} = 32-char lowercase hex from current span context
        - {span_id} = 16-char lowercase hex from current span context
        - 01 = trace flags (01 = sampled/enabled)

    Notes
    -----
    This function is safe to call at any time:
    - If a valid span context exists, returns the current trace/span IDs
    - If span context is unavailable or invalid, returns zeros for both IDs
    - Integrates with Litestar's OpenTelemetry middleware for automatic
      span propagation across async execution boundaries

    The returned header can be appended directly to HTTP responses or used
    in distributed tracing systems that understand W3C Trace Context.

    See Also
    --------
    W3C Trace Context spec: https://www.w3.org/TR/trace-context/
    """
    return f"00-{get_trace_id()}-{get_span_id()}-01"
