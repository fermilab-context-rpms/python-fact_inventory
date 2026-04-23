"""Structlog configuration for OTEL-compliant JSON logging.

Uses Litestar's StructlogPlugin with structlog's native JSON output.
"""

import logging
import os
import socket
import sys
from typing import Any

import structlog
from litestar.logging.config import StructLoggingConfig
from litestar.plugins.structlog import StructlogConfig

from fact_inventory.lib.otel import get_span_id, get_trace_id
from fact_inventory.lib.settings import settings

__all__ = ["get_structlog_config"]

#: Mapping from log level names to Python logging module integer constants.
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _add_otel_trace_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add OpenTelemetry trace context to log event.

    Injects trace_id and span_id as top-level fields per OTEL log data model.
    These fields enable correlation between logs and traces in distributed
    tracing systems.

    Parameters
    ----------
    _logger : Any
        The logger instance (unused).
    _method_name : str
        The log method name (unused).
    event_dict : dict[str, Any]
        The current event dictionary being processed.

    Returns
    -------
    dict[str, Any]
        Updated event dictionary with trace context fields added.
    """
    event_dict["trace_id"] = get_trace_id()
    event_dict["span_id"] = get_span_id()

    return event_dict


def _add_resource(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add OTEL resource attributes (service metadata) to log event.

    Resource is a top-level field in OTEL log records containing static
    information about the service that generated the log.

    Parameters
    ----------
    _logger : Any
        The logger instance (unused).
    _method_name : str
        The log method name (unused).
    event_dict : dict[str, Any]
        The current event dictionary being processed.

    Returns
    -------
    dict[str, Any]
        Updated event dictionary with resource information added.
    """
    event_dict["resource"] = {
        "service.name": settings.app_name,
        "service.version": settings.version,
        "host.name": os.getenv("HOST", socket.gethostname()),
        "deployment.environment": settings.deployment_environment,
    }

    namespace = os.getenv("SERVICE_NAMESPACE", None)
    if namespace is not None:
        event_dict["resource"]["service.namespace"] = namespace

    return event_dict


def _filter_empty_values(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Remove None values from event dictionary.

    Parameters
    ----------
    _logger : Any
        The logger instance (unused).
    _method_name : str
        The log method name (unused).
    event_dict : dict[str, Any]
        The current event dictionary being processed.

    Returns
    -------
    dict[str, Any]
        Event dictionary with None values removed.
    """
    return {k: v for k, v in event_dict.items() if v is not None}


def get_structlog_config(log_level: str = "INFO") -> StructlogConfig:
    """Create OTEL-compliant StructLogConfig for Litestar application logging.

    Parameters
    ----------
    log_level : str
        Minimum log level to emit. Valid values: "DEBUG", "INFO", "WARNING",
        "ERROR", "CRITICAL". Default: "INFO".

    Returns
    -------
    StructlogConfig
        Configured structlog with OTEL log data model compliance including
        trace context, resource attributes, JSON formatting, and log level
        filtering.

    Raises
    ------
    ValueError
        If log_level is not a recognized logging level name.
    """
    # Convert string log level to Python logging integer constant
    if log_level not in LOG_LEVEL_MAP:
        raise ValueError(  # noqa: TRY003
            f"Invalid log_level '{log_level}'. "
            f"Must be one of: {', '.join(LOG_LEVEL_MAP.keys())}"
        )
    numeric_log_level = LOG_LEVEL_MAP[log_level]

    # Structlog processor pipeline
    structlog_processors: list[Any] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_otel_trace_context,
        _add_resource,
        _filter_empty_values,
        structlog.processors.JSONRenderer(),
    ]

    # Create structlog logging config
    # Use PrintLoggerFactory with file=sys.stdout to output text (not bytes)
    # This prevents BytesLogger errors when structlog outputs JSON strings
    # Use make_filtering_bound_logger to filter by log level
    structlog_logging_config = StructLoggingConfig(
        processors=structlog_processors,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
        log_exceptions="always",
        wrapper_class=structlog.make_filtering_bound_logger(numeric_log_level),
    )

    return StructlogConfig(
        structlog_logging_config=structlog_logging_config,
        enable_middleware_logging=True,
    )
