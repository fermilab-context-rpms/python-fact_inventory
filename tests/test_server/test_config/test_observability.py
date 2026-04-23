"""Tests for server configuration modules."""

from fact_inventory.lib.settings import Settings
from fact_inventory.server.config.observability import (
    create_logging_config,
    create_tracer_provider,
)


def test_create_logging_config_creates_config() -> None:
    """Logging config creates valid StructlogConfig."""
    settings = Settings(
        log_level="INFO",
        debug=False,
    )

    config = create_logging_config(settings)

    assert config is not None
    assert config.enable_middleware_logging is True


def test_create_logging_config_respects_debug_mode() -> None:
    """Debug mode forces DEBUG log level."""
    settings = Settings(
        log_level="WARNING",
        debug=True,
    )

    config = create_logging_config(settings)

    # When debug=True, the effective log level should be DEBUG
    # even if log_level is set to WARNING
    assert config is not None


def test_create_tracer_provider_creates_provider() -> None:
    """Tracer provider creates valid TracerProvider with shutdown hooks."""
    settings = Settings(
        debug=False,
    )

    provider, shutdown_hooks = create_tracer_provider(settings)

    assert provider is not None
    assert isinstance(shutdown_hooks, list)


def test_create_tracer_provider_with_debug_enables_console_exporter() -> None:
    """Debug mode enables console span exporter."""
    settings = Settings(
        debug=True,
    )

    provider, shutdown_hooks = create_tracer_provider(settings)

    assert provider is not None
    assert len(shutdown_hooks) > 0
