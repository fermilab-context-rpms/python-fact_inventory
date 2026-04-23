"""Shared database helpers for tests."""

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.infrastructure.db.models import FactInventory

__all__ = [
    "count_records_for_client",
    "fact_inventory_query",
    "get_record_for_client",
    "get_records_for_client",
    "persist_fact_inventory",
    "truncate_fact_inventory",
]


async def truncate_fact_inventory(session: AsyncSession) -> None:
    """Delete all rows from FactInventory and commit."""
    await session.execute(delete(FactInventory))
    await session.commit()
    await asyncio.sleep(0)


async def persist_fact_inventory(
    session: AsyncSession,
    *records: FactInventory,
) -> None:
    """Persist unsaved FactInventory models in one transaction."""
    session.add_all(records)
    await session.commit()


def fact_inventory_query(client_address: str):
    """Return the canonical query for records belonging to one client."""
    return (
        select(FactInventory)
        .where(FactInventory.client_address == client_address)
        .order_by(FactInventory.created_at.desc(), FactInventory.id.desc())
    )


async def get_records_for_client(
    session: AsyncSession, client_address: str
) -> list[FactInventory]:
    """Fetch all records for a client ordered newest first."""
    result = await session.execute(fact_inventory_query(client_address))
    return list(result.scalars())


async def get_record_for_client(
    session: AsyncSession, client_address: str
) -> FactInventory:
    """Fetch exactly one record for a client."""
    result = await session.execute(fact_inventory_query(client_address))
    return result.scalar_one()


async def count_records_for_client(session: AsyncSession, client_address: str) -> int:
    """Count records for a client using the canonical query helper."""
    records = await get_records_for_client(session, client_address)
    return len(records)
