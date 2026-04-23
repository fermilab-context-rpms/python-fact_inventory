"""Application factory pattern implementation for the Litestar ASGI application.

This module is part of the server assembly layer and wires together:

- Database via SQLAlchemy async using ``advanced_alchemy``.
- Observability via OpenTelemetry and Prometheus.
- Rate limiting baked into the router via ``create_router``.
- Background job scheduler via ``AsyncBackgroundJobPlugin``.
- All route handlers.

All configuration tunables are read from the ``settings`` singleton
(see fact_inventory/lib/settings.py).

Notes
-----
Configuration is sourced from ``fact_inventory.lib`` (application infrastructure)
while application assembly and plugin wiring happens here in ``fact_inventory.server``.
"""

import logging
from typing import Any
from urllib.parse import urlparse

from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)
from advanced_alchemy.extensions.litestar.plugins.init.config.engine import EngineConfig
from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from litestar.plugins.prometheus import PrometheusConfig
from litestar.plugins.structlog import StructlogPlugin
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from fact_inventory.application.services import FactInventoryService
from fact_inventory.infrastructure.db.db_migrations import check_migrations_up_to_date
from fact_inventory.lib.logging import get_structlog_config
from fact_inventory.lib.settings import settings
from fact_inventory.presentation.metrics import FactInventoryPrometheusController
from fact_inventory.presentation.router import create_router
from fact_inventory.server.background import AsyncBackgroundJobPlugin

__all__ = ["create_app"]


async def _check_db_migrations() -> None:
    """Check that database migrations are up to date at startup.

    Raises RuntimeError if migrations need to be run.
    """
    if settings.database_uri is None:  # pragma: no cover
        raise ValueError(  # noqa: TRY003
            "DATABASE_URI is required. Set it to a valid database connection string."
        )
    await check_migrations_up_to_date(settings.database_uri)


def create_app() -> Litestar:
    """Assemble and return a fully configured Litestar ASGI application.

    The application factory pattern wires together the database plugin,
    background cleanup tasks, observability middleware (Prometheus
    optional), and rate-limited route handlers.
    All configuration tunables are read from the settings singleton.

    OpenAPI documentation is enabled only when DEBUG=true to avoid
    exposing the schema on production deployments.

    Returns
    -------
    Litestar
        Fully configured Litestar application ready to be served by
        an ASGI server.
    """

    # Database plugin setup
    parsed = urlparse(settings.database_uri)

    engine_config = EngineConfig(echo=settings.debug)
    if parsed.scheme and "sqlite" not in str(parsed.scheme):
        engine_config = EngineConfig(  # pragma: no cover
            pool_size=settings.db_pool_size,
            pool_recycle=3600,
            max_overflow=settings.db_pool_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,
            echo=settings.debug,
        )

    alchemy_config = SQLAlchemyAsyncConfig(
        engine_config=engine_config,
        connection_string=settings.database_uri,
        before_send_handler="autocommit",
        session_config=AsyncSessionConfig(expire_on_commit=True),
        create_all=False,
    )

    # Background job scheduler - retention cleanup
    async def _cleanup_expired_facts() -> int:
        """Delete facts older than the configured retention window.

        Parameters
        ----------
        None

        Returns
        -------
        int
            Number of records deleted.
        """
        async with alchemy_config.get_session() as session:
            service = FactInventoryService(session)
            return await service.purge_facts_older_than(settings.retention_days)

    retention_cleanup_plugin = AsyncBackgroundJobPlugin(
        job_callback=_cleanup_expired_facts,
        interval_seconds=settings.retention_check_interval_hours * 3600,
        jitter_seconds=settings.retention_check_jitter_minutes * 60,
        name="fact-inventory-retention-cleanup",
    )

    # Background job scheduler - history cleanup
    async def _cleanup_fact_history() -> int:
        """Delete fact history records per client_address exceeding max_entries.

        Parameters
        ----------
        None

        Returns
        -------
        int
            Number of records deleted.
        """
        async with alchemy_config.get_session() as session:
            service = FactInventoryService(session)
            return await service.purge_fact_history_more_than(
                settings.history_max_entries
            )

    history_cleanup_plugin = AsyncBackgroundJobPlugin(
        job_callback=_cleanup_fact_history,
        interval_seconds=settings.history_check_interval_hours * 3600,
        jitter_seconds=settings.history_check_jitter_minutes * 60,
        name="fact-inventory-history-cleanup",
    )

    # Logging configuration - structlog with OTEL compliance
    # DEBUG mode always forces DEBUG log level regardless of configured value
    effective_log_level = "DEBUG" if settings.debug else settings.log_level
    logging_cfg = get_structlog_config(log_level=effective_log_level)

    # Configure OpenTelemetry with a proper tracer provider
    tracer_provider = TracerProvider()
    if settings.debug:
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    otel_config = OpenTelemetryConfig(tracer_provider=tracer_provider)

    # Assemble the Litestar app
    app_kwargs: dict[str, Any] = {
        "route_handlers": [create_router(settings.app_prefix)],
        "plugins": [
            SQLAlchemyPlugin(config=alchemy_config),
            OpenTelemetryPlugin(otel_config),
            StructlogPlugin(config=logging_cfg),
        ],
        "middleware": [otel_config.middleware],
        "compression_config": CompressionConfig(
            backend="gzip",
        ),
        "logging_config": logging_cfg.structlog_logging_config,
        "openapi_config": None,
        "debug": settings.debug,
        "on_startup": [_check_db_migrations],
    }

    if settings.debug:
        app_kwargs["openapi_config"] = OpenAPIConfig(
            title=settings.app_name,
            version=settings.version,
        )

    if settings.enable_retention_cleanup_job:
        app_kwargs["plugins"].append(retention_cleanup_plugin)

    if settings.enable_history_cleanup_job:
        app_kwargs["plugins"].append(history_cleanup_plugin)

    if settings.enable_metrics:
        prometheus_config = PrometheusConfig(app_name=settings.app_name)
        app_kwargs["route_handlers"].append(FactInventoryPrometheusController)
        app_kwargs["middleware"].append(prometheus_config.middleware)

    logging.getLogger(__name__).info("Fact Inventory application starting")

    return Litestar(**app_kwargs)
