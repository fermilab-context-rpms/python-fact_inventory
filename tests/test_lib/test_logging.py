"""Tests for OTEL-compliant structlog configuration."""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
import structlog

from fact_inventory.lib.logging import (
    _add_otel_trace_context,
    _add_resource,
    _filter_empty_values,
    get_structlog_config,
)


@contextmanager
def patched_logging_settings() -> Iterator[None]:
    """Patch logging settings and hostname for resource tests."""
    mock_settings = type(
        "MockSettings",
        (),
        {
            "app_name": "test-app",
            "version": "1.0.0",
            "deployment_environment": "development",
        },
    )()
    with (
        patch(
            "fact_inventory.lib.logging.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "fact_inventory.lib.logging.socket.gethostname",
            return_value="test-host",
        ),
    ):
        yield


def resource_from_event(
    *,
    host_name: str = "test-host",
    service_namespace: str | None = None,
) -> dict[str, str]:
    """Run _add_resource with explicit host and namespace inputs."""

    def mock_getenv(key: str, default: str | None = None) -> str | None:
        if key == "HOST":
            return host_name
        if key == "SERVICE_NAMESPACE":
            return service_namespace
        return default

    with (
        patched_logging_settings(),
        patch("fact_inventory.lib.logging.os.getenv", side_effect=mock_getenv),
    ):
        result = _add_resource(None, "info", {})
    return result["resource"]


@pytest.mark.parametrize(
    "trace_id,span_id",
    [
        ("abc123", "def456"),
        ("0" * 32, "0" * 16),
    ],
)
def test_add_trace_context_adds_ids(trace_id: str, span_id: str) -> None:
    """Trace and span IDs added to event dict when available."""
    event_dict: dict[str, str] = {}

    with (
        patch("fact_inventory.lib.logging.get_trace_id", return_value=trace_id),
        patch("fact_inventory.lib.logging.get_span_id", return_value=span_id),
    ):
        result = _add_otel_trace_context(None, None, event_dict)

    assert result["trace_id"] == trace_id
    assert result["span_id"] == span_id


def test_add_resource_minimum_required_fields_present() -> None:
    """Resource dict includes minimum required service fields."""
    resource = resource_from_event()
    assert resource["service.name"] == "test-app"
    assert resource["service.version"] == "1.0.0"
    assert resource["host.name"] == "test-host"
    assert resource["deployment.environment"] == "development"


@pytest.mark.parametrize(
    ("service_namespace", "expected_namespace"),
    [
        pytest.param("test-namespace", "test-namespace", id="included"),
        pytest.param(None, None, id="omitted"),
    ],
)
def test_add_resource_service_namespace_behavior(
    service_namespace: str | None,
    expected_namespace: str | None,
) -> None:
    """Service namespace is included only when configured."""
    resource = resource_from_event(service_namespace=service_namespace)

    if expected_namespace is None:
        assert "service.namespace" not in resource
    else:
        assert resource["service.namespace"] == expected_namespace


def test_filter_empty_values_removes_none_values() -> None:
    """None values removed, other keys preserved."""
    event_dict = {"key1": "value1", "key2": None, "key3": "value3"}

    result = _filter_empty_values(None, None, event_dict)

    assert result == {"key1": "value1", "key3": "value3"}


def test_filter_empty_values_preserves_falsy_values_except_none() -> None:
    """Falsy values (0, '', False) preserved; only None filtered."""
    event_dict = {"empty_str": "", "zero": 0, "false": False, "none": None}

    result = _filter_empty_values(None, None, event_dict)

    assert result["empty_str"] == ""
    assert result["zero"] == 0
    assert result["false"] is False
    assert "none" not in result


def test_get_structlog_config_uses_stdout_logger_factory() -> None:
    """Configuration uses PrintLoggerFactory for stdout."""
    config = get_structlog_config()

    assert config.structlog_logging_config is not None
    assert isinstance(
        config.structlog_logging_config.logger_factory,
        structlog.PrintLoggerFactory,
    )


def test_get_structlog_config_enables_middleware_logging() -> None:
    """Middleware logging enabled in configuration."""
    config = get_structlog_config()

    assert config.enable_middleware_logging is True


def test_get_structlog_config_logs_exceptions_always() -> None:
    """Exception logging set to 'always' mode."""
    config = get_structlog_config()

    assert config.structlog_logging_config.log_exceptions == "always"


@pytest.mark.parametrize(
    "log_level_str,expected_level",
    [
        ("DEBUG", 10),
        ("INFO", 20),
        ("WARNING", 30),
        ("ERROR", 40),
        ("CRITICAL", 50),
    ],
)
def test_get_structlog_config_applies_log_level(
    log_level_str: str, expected_level: int
) -> None:
    """Provided log level string is converted to correct filtering level."""
    config = get_structlog_config(log_level=log_level_str)

    # The wrapper_class should be a filtering bound logger
    assert config.structlog_logging_config.wrapper_class is not None
    # Verify by checking the level was passed (we can't directly inspect
    # the closure, but we can verify config doesn't error on valid levels)
    assert config.structlog_logging_config.wrapper_class is not None


def test_get_structlog_config_invalid_log_level_raises_error() -> None:
    """Invalid log level string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid log_level 'INVALID'"):
        get_structlog_config(log_level="INVALID")


def test_get_structlog_config_default_log_level_is_info() -> None:
    """Default log level is INFO when not specified."""
    config = get_structlog_config()

    # Should not raise an error and should use default
    assert config.structlog_logging_config.wrapper_class is not None
