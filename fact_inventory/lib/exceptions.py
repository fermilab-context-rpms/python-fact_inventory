"""Application infrastructure exceptions.

These exceptions express business rule violations without any HTTP or
framework dependency. The presentation layer is responsible for mapping
them to the appropriate HTTP response codes.

Notes
-----
This module is part of the application infrastructure layer (lib/) and
provides shared exception types used across domain and application layers.
"""

__all__ = ["FactValidationError", "MigrationNotUpToDateError"]


class FactValidationError(ValueError):
    """Raised when submitted facts fail business validation.

    Used when all fact categories (system_facts, package_facts,
    local_facts, agent_facts) are empty, which violates the rule that
    a submission must contain at least one category of data.
    """

    pass


class MigrationNotUpToDateError(RuntimeError):
    """Raised when database migrations are not up to date."""

    def __init__(self, current_revision: str | None, head_revision: str) -> None:
        """Initialize error with revision information.

        Parameters
        ----------
        current_revision : str | None
            Current database revision, or None if no migrations have run.
        head_revision : str
            Latest migration revision in the migrations/ directory.
        """
        self.current_revision = current_revision
        self.head_revision = head_revision
        msg = (
            f"Database migrations not up to date.\n"
            f"Current revision: {current_revision or 'None (no migrations applied)'}\n"
            f"Head revision: {head_revision}\n"
            f"\n"
            f"To setup the database, run:\n"
            f"  litestar --app fact_inventory:app database upgrade"
        )
        super().__init__(msg)
