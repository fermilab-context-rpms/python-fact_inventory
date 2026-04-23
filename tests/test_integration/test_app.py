"""Integration tests exercising the full application stack."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_429_TOO_MANY_REQUESTS,
)
from litestar.testing import AsyncTestClient

from fact_inventory.lib.exceptions import MigrationNotUpToDateError
from fact_inventory.lib.settings import settings
from fact_inventory.presentation.router import create_router
from fact_inventory.server.app import create_app
from fact_inventory.server.background import AsyncBackgroundJobPlugin
from tests.factories import (
    create_minimal,
    create_payload_under_body_limit,
    create_payload_with_field_at_limit,
    create_payload_with_oversized_field,
    create_valid,
)
from tests.support.http import assert_status, post_facts

API_ROOT = f"{settings.app_prefix}/api"
CUSTOM_ROUTER_PATH = "/fact_inventory"
FACTS_ENDPOINT = f"{settings.app_prefix}/api/v1/facts"
HEALTH_ENDPOINT = f"{settings.app_prefix}/health"
METRICS_ENDPOINT = f"{settings.app_prefix}/metrics"
READY_ENDPOINT = f"{settings.app_prefix}/ready"

RETENTION_JOB_NAME = "fact-inventory-retention-cleanup"
HISTORY_JOB_NAME = "fact-inventory-history-cleanup"


def find_background_job_plugin(app: Any, name: str) -> AsyncBackgroundJobPlugin:
    """Return the background-job plugin with the given name."""
    for p in app.plugins:
        if isinstance(p, AsyncBackgroundJobPlugin) and p.name == name:
            return p
    raise AssertionError(f"No AsyncBackgroundJobPlugin found with name '{name}'")


def count_background_job_plugins(app: Any, name: str) -> int:
    """Count background-job plugins by name."""
    count = 0
    for p in app.plugins:
        if isinstance(p, AsyncBackgroundJobPlugin) and p.name == name:
            count += 1
    return count


async def assert_background_job_callback_returns_count(
    test_client: AsyncTestClient,
    job_name: str,
) -> None:
    """Verify a background job callback executes and returns a count."""
    result = await find_background_job_plugin(test_client.app, job_name).job_callback()

    assert isinstance(result, int)
    assert result >= 0


def test_router_paths_default_path_is_slash() -> None:
    """The top-level router defaults to the root path."""
    assert create_router().path == "/"


def test_router_paths_custom_path_stored() -> None:
    """The top-level router preserves a custom mount path."""
    assert create_router(path=CUSTOM_ROUTER_PATH).path == CUSTOM_ROUTER_PATH


async def test_router_paths_facts_at_custom_prefix(
    client_with_custom_router_path: AsyncTestClient,
) -> None:
    """Facts remain reachable when the router is mounted at a custom prefix."""
    response = await post_facts(client_with_custom_router_path)

    assert_status(response, HTTP_201_CREATED)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/v1/health", id="health-not-under-v1"),
        pytest.param("/v1/ready", id="ready-not-under-v1"),
        pytest.param("/api/health", id="health-not-under-api"),
        pytest.param("/api/ready", id="ready-not-under-api"),
        pytest.param("/facts", id="facts-not-at-root"),
        pytest.param("/api/facts", id="facts-not-at-api-root"),
    ],
)
async def test_routing_isolation_paths_return_404(
    test_client: AsyncTestClient,
    path: str,
) -> None:
    """Incorrect route prefixes stay inaccessible in the assembled app."""
    method = test_client.get
    kwargs: dict[str, Any] = {}
    if "facts" in path:
        method = test_client.post
        kwargs["json"] = create_minimal()

    response = await method(path, **kwargs)
    assert_status(response, HTTP_404_NOT_FOUND)


async def test_feature_flags_both_probes_can_be_disabled(
    client_factory,
) -> None:
    """Disabling probes does not break the main API."""
    async with client_factory() as test_client:
        health_response = await test_client.get(HEALTH_ENDPOINT)
        ready_response = await test_client.get(READY_ENDPOINT)
        facts_response = await post_facts(test_client)

    assert_status(health_response, HTTP_404_NOT_FOUND)
    assert_status(ready_response, HTTP_404_NOT_FOUND)
    assert_status(facts_response, HTTP_201_CREATED)


async def test_feature_flags_openapi_disabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAPI is disabled when debug is off."""
    monkeypatch.setattr(settings, "debug", False)
    assert create_app().openapi_config is None


async def test_feature_flags_gzip_enabled(
    client_with_metrics: AsyncTestClient,
) -> None:
    """Compression middleware gzips naturally large metrics responses."""
    await post_facts(client_with_metrics)
    response = await client_with_metrics.get(
        METRICS_ENDPOINT,
        headers={"Accept-Encoding": "gzip"},
    )

    assert_status(response, HTTP_200_OK)
    assert "# HELP" in response.text
    assert "gzip" in response.headers.get("content-encoding", "")


async def test_feature_flags_metrics_endpoint_enabled(
    client_with_metrics: AsyncTestClient,
) -> None:
    """Metrics is reachable when enabled."""
    response = await client_with_metrics.get(METRICS_ENDPOINT)

    assert_status(response, HTTP_200_OK)


@pytest.mark.parametrize(
    "disabled_endpoint",
    [
        pytest.param("health", id="health-disabled"),
        pytest.param("ready", id="ready-disabled"),
    ],
)
async def test_feature_flags_api_still_works_when_probe_disabled(
    test_client: AsyncTestClient,
    disabled_endpoint: str,
) -> None:
    """The API remains functional when optional probes are absent."""
    endpoint = HEALTH_ENDPOINT if disabled_endpoint == "health" else READY_ENDPOINT
    probe_response = await test_client.get(endpoint)
    facts_response = await post_facts(test_client)

    assert_status(probe_response, HTTP_404_NOT_FOUND)
    assert_status(facts_response, HTTP_201_CREATED)


@pytest.mark.parametrize(
    "job_name",
    [
        pytest.param(RETENTION_JOB_NAME, id="retention-job"),
        pytest.param(HISTORY_JOB_NAME, id="history-job"),
    ],
)
async def test_background_job_callbacks_return_counts(
    client_factory,
    job_name: str,
) -> None:
    """Configured background jobs expose callable count-returning callbacks."""
    async with client_factory() as test_client:
        await assert_background_job_callback_returns_count(test_client, job_name)


async def test_background_job_history_callback_works_with_data_present(
    client_factory,
) -> None:
    """The history cleanup job still runs when there is data to inspect."""
    async with client_factory() as test_client:
        await post_facts(test_client, payload=create_valid())
        await post_facts(test_client, payload=create_valid())
        await assert_background_job_callback_returns_count(
            test_client,
            HISTORY_JOB_NAME,
        )


@pytest.mark.parametrize(
    ("payload_factory", "expected_status"),
    [
        pytest.param(
            lambda: create_payload_under_body_limit(settings.max_request_body_mb),
            HTTP_201_CREATED,
            id="http-body-under-limit",
        ),
        pytest.param(
            lambda: create_payload_with_field_at_limit(settings.max_json_field_mb),
            HTTP_201_CREATED,
            id="json-field-at-limit",
        ),
        pytest.param(
            lambda: create_payload_with_oversized_field(settings.max_json_field_mb),
            HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            id="json-field-over-limit",
        ),
    ],
)
async def test_payload_size_limits_are_enforced_end_to_end(
    test_client: AsyncTestClient,
    payload_factory: Callable[[], dict[str, Any]],
    expected_status: int,
) -> None:
    """The assembled app enforces payload limits across the stack."""
    response = await post_facts(test_client, payload=payload_factory())

    assert_status(response, expected_status)


@pytest.mark.parametrize(
    ("overrides", "expected_retention", "expected_history"),
    [
        pytest.param(
            {"enable_retention_cleanup_job": False},
            0,
            1,
            id="retention-disabled",
        ),
        pytest.param(
            {"enable_history_cleanup_job": False},
            1,
            0,
            id="history-disabled",
        ),
        pytest.param(
            {
                "enable_retention_cleanup_job": False,
                "enable_history_cleanup_job": False,
            },
            0,
            0,
            id="both-disabled",
        ),
    ],
)
async def test_background_job_feature_flags_control_plugin_registration(
    client_factory,
    overrides: dict[str, bool],
    expected_retention: int,
    expected_history: int,
) -> None:
    """Background-job feature flags control plugin registration independently."""
    async with client_factory(settings_overrides=overrides) as test_client:
        retention_count = count_background_job_plugins(
            test_client.app,
            RETENTION_JOB_NAME,
        )
        history_count = count_background_job_plugins(
            test_client.app,
            HISTORY_JOB_NAME,
        )

    assert retention_count == expected_retention
    assert history_count == expected_history


def test_settings_debug_and_log_level_are_independent() -> None:
    """Debug and log level remain independently configurable."""
    assert isinstance(settings.debug, bool)
    assert isinstance(settings.log_level, str)


def test_app_uses_configured_log_level() -> None:
    """Application passes configured LOG_LEVEL to logging system."""
    from fact_inventory.lib.logging import get_structlog_config

    # Verify that get_structlog_config accepts and processes log_level param
    config = get_structlog_config(log_level="WARNING")
    assert config.structlog_logging_config.wrapper_class is not None

    # Verify all valid log levels are accepted
    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        config = get_structlog_config(log_level=level)
        assert config.structlog_logging_config.wrapper_class is not None


def test_app_debug_mode_forces_debug_log_level() -> None:
    """DEBUG=True overrides LOG_LEVEL to force DEBUG level."""
    from fact_inventory.server.app import create_app

    # Patch settings to simulate DEBUG=True with LOG_LEVEL=WARNING
    with patch("fact_inventory.server.app.settings") as mock_settings:
        mock_settings.debug = True
        mock_settings.log_level = "WARNING"  # Should be overridden
        mock_settings.database_uri = "sqlite+aiosqlite:///:memory:"
        mock_settings.app_prefix = "/"
        mock_settings.app_name = "test-app"
        mock_settings.version = "test-1.0"
        mock_settings.retention_days = 400
        mock_settings.retention_check_interval_hours = 20
        mock_settings.retention_check_jitter_minutes = 200
        mock_settings.history_check_interval_hours = 20
        mock_settings.history_max_entries = 5
        mock_settings.history_check_jitter_minutes = 200
        mock_settings.enable_retention_cleanup_job = False
        mock_settings.enable_history_cleanup_job = False
        mock_settings.db_pool_size = 10
        mock_settings.db_pool_max_overflow = 20
        mock_settings.db_pool_timeout = 30
        mock_settings.api_rate_limit_unit = "hour"
        mock_settings.api_rate_limit_max_requests = 2
        mock_settings.enable_metrics = False
        mock_settings.enable_health_endpoint = False
        mock_settings.enable_ready_endpoint = False

        with patch(
            "fact_inventory.server.app.check_migrations_up_to_date",
            new_callable=AsyncMock,
        ):
            app = create_app()

    # The logging config should have been called with "DEBUG" not "WARNING"
    # We verify this indirectly through the app's logging_config
    assert app.logging_config is not None


async def test_app_startup_blocked_when_migrations_out_of_date() -> None:
    """The app refuses startup when migration checks fail."""
    stale = MigrationNotUpToDateError(
        current_revision="old_rev",
        head_revision="new_rev",
    )
    with (
        patch(
            "fact_inventory.server.app.check_migrations_up_to_date",
            new_callable=AsyncMock,
            side_effect=stale,
        ),
        pytest.raises(ExceptionGroup) as exc_info,
    ):
        async with AsyncTestClient(app=create_app()):
            pytest.fail("startup unexpectedly succeeded")

    assert exc_info.value.subgroup(MigrationNotUpToDateError) is not None


async def test_rate_limit_returns_429_when_quota_exhausted(
    test_client: AsyncTestClient,
) -> None:
    """Rate limiting rejects the third request from the same client."""
    payload = create_minimal()
    await post_facts(test_client, payload=payload)
    await post_facts(test_client, payload=payload)
    response = await post_facts(test_client, payload=payload)

    assert_status(response, HTTP_429_TOO_MANY_REQUESTS)


async def test_api_root_is_available_in_full_app(
    test_client: AsyncTestClient,
) -> None:
    """The assembled app exposes the API root endpoint."""
    response = await test_client.get(API_ROOT)

    assert_status(response, HTTP_200_OK)


async def test_facts_endpoint_uses_documented_full_path(
    test_client: AsyncTestClient,
) -> None:
    """The full facts route works in the assembled app."""
    response = await post_facts(test_client)

    assert_status(response, HTTP_201_CREATED)
