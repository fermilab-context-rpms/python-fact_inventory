"""Background job factory for fact retention cleanup.

Creates a configured AsyncBackgroundJobPlugin that periodically deletes
facts older than the configured retention window.
"""

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig

from fact_inventory.application.services.fact import FactInventoryService
from fact_inventory.lib.settings import Settings
from fact_inventory.server.background_job.lock import run_exclusive_background_job
from fact_inventory.server.background_job.plugin import AsyncBackgroundJobPlugin

__all__ = ["create_retention_cleanup_job"]


def create_retention_cleanup_job(
    settings: Settings, alchemy_config: SQLAlchemyAsyncConfig
) -> AsyncBackgroundJobPlugin:
    """Create retention cleanup background job plugin.

    Parameters
    ----------
    settings : Settings
        Application settings including retention configuration.
    alchemy_config : SQLAlchemyAsyncConfig
        Database configuration for session management.

    Returns
    -------
    AsyncBackgroundJobPlugin
        Configured plugin for expired fact cleanup.
    """

    async def _cleanup_expired_facts() -> int:
        """Delete facts older than the configured retention window.

        Returns
        -------
        int
            Number of records deleted.
        """

        async def _run_retention_cleanup() -> int:
            async with alchemy_config.get_session() as session:
                service = FactInventoryService(session, settings=settings)
                return await service.purge_facts_older_than(settings.retention_days)

        return await run_exclusive_background_job(
            alchemy_config=alchemy_config,
            name="fact-inventory-retention-cleanup",
            interval_seconds=settings.retention_check_interval_hours * 3600,
            work=_run_retention_cleanup,
        )

    return AsyncBackgroundJobPlugin(
        job_callback=_cleanup_expired_facts,
        interval_seconds=settings.retention_check_interval_hours * 3600,
        jitter_seconds=settings.retention_check_jitter_minutes * 60,
        name="fact-inventory-retention-cleanup",
    )
