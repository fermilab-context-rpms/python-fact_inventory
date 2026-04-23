"""Observability configuration for the fact_inventory server.

Provides logging, OpenTelemetry, and tracing setup.
"""

from typing import Any

from litestar.plugins.structlog import StructlogConfig
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from fact_inventory.lib.logging import get_structlog_config
from fact_inventory.lib.settings import Settings

__all__ = ["create_logging_config", "create_tracer_provider"]


def create_logging_config(settings: Settings) -> StructlogConfig:
    """Create structlog configuration.

    Parameters
    ----------
    settings : Settings
        Application settings including log level.

    Returns
    -------
    StructlogConfig
        Configured structlog with OTEL log data model compliance.
    """
    effective_log_level = "DEBUG" if settings.debug else settings.log_level
    return get_structlog_config(log_level=effective_log_level)


def create_tracer_provider(settings: Settings) -> tuple[TracerProvider, list[Any]]:
    """Create OpenTelemetry tracer provider and shutdown hooks.

    Parameters
    ----------
    settings : Settings
        Application settings (debug mode controls span export).

    Returns
    -------
    tuple[TracerProvider, list]
        Tracer provider and list of shutdown callables.
    """
    tracer_provider = TracerProvider()
    shutdown_hooks = []

    if settings.debug:
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    async def _shutdown_tracer_provider() -> None:
        """Flush and shut down the OpenTelemetry tracer provider."""
        tracer_provider.shutdown()

    shutdown_hooks.append(_shutdown_tracer_provider)

    return tracer_provider, shutdown_hooks
