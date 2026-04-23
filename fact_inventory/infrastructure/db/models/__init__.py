"""Database models for the application tables.

This package defines the ORM entity layer. Models map database tables to
Python classes and handle schema definition. They do not contain business
logic - that belongs in services.
"""

from fact_inventory.infrastructure.db.models.background_job_lock import (
    BackgroundJobLock,
)
from fact_inventory.infrastructure.db.models.fact_inventory import FactInventory

__all__ = [
    "BackgroundJobLock",
    "FactInventory",
]
