"""Tests for FactInventoryRepository database operations."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.domain.retention.history import HistoryRetentionPolicy
from fact_inventory.domain.retention.time import TimeRetentionPolicy
from fact_inventory.infrastructure.db.models import FactInventory
from fact_inventory.infrastructure.db.repositories import FactInventoryRepository
from tests.factories import build_fact_model, create_record
from tests.fixtures import parametrize_ipv4_ipv6
from tests.support.db import (
    count_records_for_client,
    get_record_for_client,
    get_records_for_client,
    persist_fact_inventory,
)


@parametrize_ipv4_ipv6()
async def test_insert_record_creates_record(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Insert stores a new row with the provided facts."""
    result = await repo.insert_record(
        create_record(
            test_ips["first"],
            system_facts={"os": "RHEL"},
            package_facts={"curl": "7.68"},
            local_facts={"k": "v"},
        )
    )

    assert result.client_address == test_ips["first"]
    assert result.system_facts == {"os": "RHEL"}


@parametrize_ipv4_ipv6()
async def test_insert_record_allows_multiple_rows_same_ip(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Insert preserves history by creating distinct rows per write."""
    payload = create_record(test_ips["second"])

    first = await repo.insert_record(payload)
    second = await repo.insert_record(payload)
    third = await repo.insert_record(payload)

    assert len({first.id, second.id, third.id}) == 3


@parametrize_ipv4_ipv6()
async def test_insert_record_returns_fact_inventory_instance(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Insert returns the ORM model instance persisted by the repository."""
    result = await repo.insert_record(create_record(test_ips["third"]))

    assert isinstance(result, FactInventory)
    assert result.id is not None


async def test_insert_record_accepts_full_form_ipv6(
    repo: FactInventoryRepository,
) -> None:
    """The client_address column accepts a full IPv6 literal."""
    full_ipv6 = "2001:0db8:0000:0000:0000:0000:0000:0001"

    result = await repo.insert_record(
        create_record(full_ipv6, system_facts={"os": "RHEL"})
    )

    assert result.client_address == full_ipv6


@parametrize_ipv4_ipv6()
async def test_upsert_record_creates_when_not_exists(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Upsert inserts a row when the client is new."""
    result = await repo.upsert_client_record(
        create_record(
            test_ips["upsert"],
            system_facts={"os": "RHEL"},
        )
    )

    assert result.client_address == test_ips["upsert"]


@parametrize_ipv4_ipv6()
async def test_upsert_record_updates_when_exists(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Upsert updates the existing row for the same client."""
    client_address = test_ips["first"]
    first = await repo.upsert_client_record(
        create_record(client_address, system_facts={"v": "1"})
    )
    second = await repo.upsert_client_record(
        create_record(client_address, system_facts={"v": "2"})
    )

    assert second.id == first.id
    assert second.system_facts == {"v": "2"}


@parametrize_ipv4_ipv6()
async def test_upsert_record_preserves_id_across_upserts(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Repeated upserts target the same row."""
    client_address = test_ips["second"]
    payload = create_record(client_address)

    first_id = (await repo.upsert_client_record(payload)).id
    second_id = (await repo.upsert_client_record(payload)).id

    assert second_id == first_id


@parametrize_ipv4_ipv6()
async def test_upsert_record_refreshes_updated_at_on_update(
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Upsert refreshes updated_at when updating an existing row."""
    client_address = test_ips["third"]
    first = await repo.upsert_client_record(
        create_record(client_address, system_facts={"v": "1"})
    )
    original_updated_at = first.updated_at

    await asyncio.sleep(0.1)
    second = await repo.upsert_client_record(
        create_record(client_address, system_facts={"v": "2"})
    )

    assert second.id == first.id
    assert second.updated_at > original_updated_at


@parametrize_ipv4_ipv6()
async def test_delete_facts_older_than_removes_expired_records(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Time-based delete removes only expired rows."""
    expired_client = test_ips["first"]
    recent_client = test_ips["second"]
    await persist_fact_inventory(
        test_db_session,
        build_fact_model(expired_client, days_offset=10),
        build_fact_model(recent_client, days_offset=2),
    )

    assert await repo.delete_facts_older_than(TimeRetentionPolicy(5)) == 1
    assert await count_records_for_client(test_db_session, expired_client) == 0
    assert await count_records_for_client(test_db_session, recent_client) == 1


@parametrize_ipv4_ipv6()
async def test_delete_facts_older_than_keeps_recent_records(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Time-based delete leaves non-expired rows in place."""
    client_address = test_ips["third"]
    await persist_fact_inventory(
        test_db_session,
        build_fact_model(client_address, days_offset=2),
    )

    assert await repo.delete_facts_older_than(TimeRetentionPolicy(10)) == 0
    assert await count_records_for_client(test_db_session, client_address) == 1


@parametrize_ipv4_ipv6()
async def test_delete_facts_older_than_removes_all_when_all_expired(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """Time-based delete removes all expired rows."""
    expired_clients = [test_ips["first"], test_ips["second"], test_ips["third"]]
    models = []
    for ip in expired_clients:
        models.append(build_fact_model(ip, days_offset=10))
    await persist_fact_inventory(test_db_session, *models)

    assert await repo.delete_facts_older_than(TimeRetentionPolicy(5)) == 3


async def test_delete_facts_older_than_empty_table_returns_zero(
    repo: FactInventoryRepository,
) -> None:
    """Time-based delete is a no-op for an empty table."""
    assert await repo.delete_facts_older_than(TimeRetentionPolicy(5)) == 0


@parametrize_ipv4_ipv6()
async def test_delete_facts_over_limit_removes_excess_per_single_client(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """History delete removes the oldest rows beyond the configured limit."""
    client_address = test_ips["history"]
    models = []
    for index in range(5):
        models.append(build_fact_model(client_address, days_offset=index))
    await persist_fact_inventory(test_db_session, *models)

    assert await repo.delete_old_client_facts_over_limit(HistoryRetentionPolicy(3)) == 2
    assert await count_records_for_client(test_db_session, client_address) == 3


@parametrize_ipv4_ipv6()
async def test_delete_facts_over_limit_window_function_partition_independence(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """History delete applies the limit independently per client."""
    client_addresses = [test_ips["upsert"], test_ips["second"]]
    models = []
    for client_address in client_addresses:
        for index in range(5):
            models.append(
                build_fact_model(
                    client_address,
                    days_offset=5 - index,
                    system_facts={"client": client_address, "i": index},
                )
            )
    await persist_fact_inventory(test_db_session, *models)

    assert await repo.delete_old_client_facts_over_limit(HistoryRetentionPolicy(3)) == 4
    for client_address in client_addresses:
        assert await count_records_for_client(test_db_session, client_address) == 3


@parametrize_ipv4_ipv6()
async def test_delete_facts_over_limit_window_function_keeps_newest(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """History delete keeps the newest rows by created_at descending."""
    client_address = test_ips["first"]
    models = []
    for index in range(5):
        models.append(
            build_fact_model(
                client_address,
                days_offset=4 - index,
                system_facts={"idx": index},
            )
        )
    await persist_fact_inventory(test_db_session, *models)

    deleted = await repo.delete_old_client_facts_over_limit(HistoryRetentionPolicy(3))
    remaining = await get_records_for_client(test_db_session, client_address)

    assert deleted == 2
    values = []
    for record in remaining:
        values.append(record.system_facts["idx"])
    assert values == [4, 3, 2]


@parametrize_ipv4_ipv6()
async def test_delete_facts_over_limit_keeps_database_rows_queryable(
    test_db_session: AsyncSession,
    repo: FactInventoryRepository,
    test_ips: dict[str, str],
) -> None:
    """The surviving newest row remains directly queryable after pruning."""
    client_address = test_ips["first"]
    models = []
    for index in range(5):
        models.append(
            build_fact_model(
                client_address,
                days_offset=4 - index,
                system_facts={"idx": index},
            )
        )
    await persist_fact_inventory(test_db_session, *models)

    await repo.delete_old_client_facts_over_limit(HistoryRetentionPolicy(1))
    record = await get_record_for_client(test_db_session, client_address)

    assert record.system_facts == {"idx": 4}
