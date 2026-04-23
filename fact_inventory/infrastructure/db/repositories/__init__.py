"""Database access layer for application tables.

This package encapsulates all database-specific query logic including raw SQL
constructs, dialect-specific hints, window functions, and query optimization.
This layer isolates the application from storage details, allowing the schema
and query strategies to evolve without changing business logic in services or
endpoints.
"""

from fact_inventory.infrastructure.db.repositories.background_job_lock import (
    BackgroundJobLockRepository,
)
from fact_inventory.infrastructure.db.repositories.fact_inventory import (
    FactInventoryRepository,
)

__all__ = [
    "BackgroundJobLockRepository",
    "FactInventoryRepository",
]
