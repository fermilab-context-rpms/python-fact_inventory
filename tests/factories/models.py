"""Factory for creating FactInventory ORM model instances.

Models are unsaved. Use session.add() and await session.commit() to persist.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fact_inventory.infrastructure.db.models import FactInventory

__all__ = [
    "build",
]


def build(  # noqa: PLR0913, PLR0917
    client_address: str,
    days_offset: int = 0,
    system_facts: dict[str, Any] | None = None,
    package_facts: dict[str, Any] | None = None,
    local_facts: dict[str, Any] | None = None,
    client_facts: dict[str, Any] | None = None,
) -> FactInventory:
    """Create unsaved model instance. Timestamps offset by days_offset days."""
    base_time = datetime.now(tz=UTC) - timedelta(days=days_offset)
    return FactInventory(
        client_address=client_address,
        system_facts=system_facts or {},
        package_facts=package_facts or {},
        local_facts=local_facts or {},
        client_facts=client_facts or {},
        created_at=base_time,
        updated_at=base_time,
    )
