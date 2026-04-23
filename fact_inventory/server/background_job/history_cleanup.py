"""Background job factory for fact history cleanup.

Creates a configured AsyncBackgroundJobPlugin that periodically deletes
excess fact history records per client_address.
"""

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig

from fact_inventory.application.services.fact import FactInventoryService
from fact_inventory.lib.settings import Settings
from fact_inventory.server.background_job.lock import run_exclusive_background_job
from fact_inventory.server.background_job.plugin import AsyncBackgroundJobPlugin

__all__ = ["create_history_cleanup_job"]


def create_history_cleanup_job(
    settings: Settings, alchemy_config: SQLAlchemyAsyncConfig
) -> AsyncBackgroundJobPlugin:
    """Create history cleanup background job plugin.

    Parameters
    ----------
    settings : Settings
        Application settings including history configuration.
    alchemy_config : SQLAlchemyAsyncConfig
        Database configuration for session management.

    Returns
    -------
    AsyncBackgroundJobPlugin
        Configured plugin for fact history cleanup.
    """

    async def _cleanup_fact_history() -> int:
        """Delete fact history records per client_address exceeding max_entries.

        Returns
        -------
        int
            Number of records deleted.
        """

        async def _run_history_cleanup() -> int:
            async with alchemy_config.get_session() as session:
                service = FactInventoryService(session, settings=settings)
                return await service.purge_fact_history_more_than(
                    settings.history_max_entries
                )

        return await run_exclusive_background_job(
            alchemy_config=alchemy_config,
            name="fact-inventory-history-cleanup",
            interval_seconds=settings.history_check_interval_hours * 3600,
            work=_run_history_cleanup,
        )

    return AsyncBackgroundJobPlugin(
        job_callback=_cleanup_fact_history,
        interval_seconds=settings.history_check_interval_hours * 3600,
        jitter_seconds=settings.history_check_jitter_minutes * 60,
        name="fact-inventory-history-cleanup",
    )
