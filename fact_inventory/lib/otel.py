"""Request context management for observability.

Provides access to OpenTelemetry trace context for distributed tracing.
Integrates with Litestar's OpenTelemetry middleware to automatically track
trace_id across async execution.
"""

from opentelemetry import trace

__all__ = ["get_span_id", "get_trace_id"]


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
