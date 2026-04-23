"""Tests for background job factory functions."""

from fact_inventory.lib.settings import Settings
from fact_inventory.server.background_job.history_cleanup import (
    create_history_cleanup_job,
)


def test_create_history_cleanup_job_creates_plugin() -> None:
    """History cleanup factory creates AsyncBackgroundJobPlugin."""
    settings = Settings(
        history_max_entries=10,
        history_check_interval_hours=24,
        history_check_jitter_minutes=20,
    )

    plugin = create_history_cleanup_job(settings, None)

    assert plugin is not None
    assert plugin.name == "fact-inventory-history-cleanup"
