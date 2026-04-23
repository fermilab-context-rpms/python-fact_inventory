"""Core FactInventoryService class.

This module contains the main service class that combines all functionality.
"""

import logging
from typing import Any

from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from fact_inventory.domain.retention.history import HistoryRetentionPolicy
from fact_inventory.domain.retention.time import TimeRetentionPolicy
from fact_inventory.domain.validation.size import JsonPayloadSizeValidator
from fact_inventory.infrastructure.db.models import FactInventory
from fact_inventory.infrastructure.db.repositories import FactInventoryRepository
from fact_inventory.lib.settings import Settings, get_settings

__all__ = ["FactInventoryService"]

logger = logging.getLogger(__name__)


class FactInventoryService(
    SQLAlchemyAsyncRepositoryService[FactInventory, FactInventoryRepository],
):
    """Business-logic layer for fact inventory records.

    Methods in this class express application rules (validation, retention
    policy, etc.) while delegating database-specific work to
    FactInventoryRepository. Records are append-only: each submission inserts
    a new row rather than updating an existing one.

    Notes
    -----
    The service layer is framework-agnostic. It uses domain objects for business
    rules and repositories for database access.
    """

    repository_type = FactInventoryRepository

    def __init__(
        self, *args: Any, settings: Settings | None = None, **kwargs: Any
    ) -> None:
        """Initialize the service with domain constraints.

        Supplied settings configure JSON validation for this service instance.

        Parameters
        ----------
        *args : Any
            Positional arguments passed to the parent SQLAlchemyAsyncRepositoryService.
        **kwargs : Any
            Keyword arguments passed to the parent SQLAlchemyAsyncRepositoryService.
        settings : Settings | None
            Application settings used to configure JSON field validation.
        """
        super().__init__(*args, **kwargs)
        app_settings = settings or get_settings()
        self._json_field_constraint = JsonPayloadSizeValidator(
            app_settings.max_json_field_mb
        )

    def _validate_json_field_constraints(self, data: dict[str, Any]) -> None:
        """Validate JSON data against all configured constraints.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing system_facts, package_facts, local_facts,
            and client_facts.

        Raises
        ------
        FactValidationError
            If all fact categories are empty.
        ValueError
            If any JSON field exceeds the configured size limit.
        """
        self._json_field_constraint.validate_json_fields(data)

    async def purge_facts_older_than(self, retention_days: int) -> int:
        """Delete fact records not updated within the specified retention window.

        Parameters
        ----------
        retention_days : int
            Records with updated_at older than this many days in the
            past are deleted.
            See ``fact_inventory.domain.retention.TimeRetentionPolicy``
            for the authoritative constraint values.

        Returns
        -------
        int
            Number of records deleted. All timestamp comparisons use UTC.

        Raises
        ------
        RepositoryError
            If the record could not be deleted (e.g., database connection error).
        SQLAlchemyError
            If database persistence fails for any reason.
        ValueError
            If retention_days is outside the valid range defined by
            ``TimeRetentionPolicy.MIN_DAYS`` and ``TimeRetentionPolicy.MAX_DAYS``.
        """
        policy = TimeRetentionPolicy(retention_days)

        # The repository commits after each batch; no wrapping transaction here.
        deleted_count = await self.repository.delete_facts_older_than(policy)
        if deleted_count > 0:
            logger.info(
                "%i Stale fact records removed by retention policy", deleted_count
            )
        return deleted_count

    async def purge_fact_history_more_than(self, max_entries: int) -> int:
        """Delete excess fact records per client_address from history.

        Keeps the newest max_entries per client_address, deletes older ones.

        Parameters
        ----------
        max_entries : int
            Maximum records to keep per client_address.
            See ``fact_inventory.domain.retention.HistoryRetentionPolicy``
            for the authoritative constraint values.

        Returns
        -------
        int
            Number of records deleted.

        Raises
        ------
        RepositoryError
            If the record could not be deleted (e.g., database connection error).
        SQLAlchemyError
            If database persistence fails for any reason.
        ValueError
            If max_entries is outside the valid range defined by
            ``HistoryRetentionPolicy.MIN_ENTRIES`` and
            ``HistoryRetentionPolicy.MAX_ENTRIES``.
        """
        policy = HistoryRetentionPolicy(max_entries)

        # The repository commits after each batch; no wrapping transaction here.
        deleted_count = await self.repository.delete_old_client_facts_over_limit(policy)
        if deleted_count > 0:
            logger.info("%i Excess fact history removed per client", deleted_count)
        return deleted_count

    async def insert_record(self, data: dict[str, Any]) -> FactInventory:
        """Insert a new fact inventory record.

        Creates a new record with the provided fact data. Multiple rows may
        exist for the same client_address - each call creates a new row with
        a unique UUID generated by the database.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing client_address, system_facts, package_facts,
            local_facts, and agent_facts.

        Returns
        -------
        FactInventory
            The newly created record with database-generated fields populated.

        Raises
        ------
        FactValidationError
            If all fact categories are empty.
        FactPayloadTooLargeError
            If any JSON field exceeds the configured size limit.
        RepositoryError
            If the record could not be created (e.g., database connection error).
        SQLAlchemyError
            If database persistence fails for any reason.
        """
        self._validate_json_field_constraints(data)
        async with self.repository.session.begin():
            record = await self.repository.insert_record(data)
        logger.info("Fact inventory record %s inserted successfully", record.id)
        return record
