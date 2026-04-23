"""Tests for background job factory functions."""

from fact_inventory.lib.settings import Settings
from fact_inventory.server.background_job.retain_cleanup import (
    create_retention_cleanup_job,
)


def test_create_retention_cleanup_job_creates_plugin() -> None:
    """Retention cleanup factory creates AsyncBackgroundJobPlugin."""
    settings = Settings(
        retention_days=365,
        retention_check_interval_hours=24,
        retention_check_jitter_minutes=20,
    )

    plugin = create_retention_cleanup_job(settings, None)

    assert plugin is not None
    assert plugin.name == "fact-inventory-retention-cleanup"
