"""Tests for BackgroundJobLockRepository database operations."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from fact_inventory.infrastructure.db.models import BackgroundJobLock
from fact_inventory.infrastructure.db.repositories import BackgroundJobLockRepository

DEFAULT_INTERVAL_SECONDS = 60


async def _get_lock(session: AsyncSession, name: str) -> BackgroundJobLock | None:
    """Fetch a lock row by name."""
    result = await session.execute(
        select(BackgroundJobLock).where(BackgroundJobLock.name == name)
    )
    return result.scalar_one_or_none()


async def _count_locks(session: AsyncSession) -> int:
    """Return the total number of rows in background_job_lock."""
    result = await session.execute(select(func.count()).select_from(BackgroundJobLock))
    count = result.scalar()
    if count is None:
        return 0
    return count


async def test_acquire_lock_creates_row_and_returns_lock(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Acquiring a free lock inserts a row and returns the lock instance."""
    lock = await lock_repo.acquire("test-job", DEFAULT_INTERVAL_SECONDS)

    assert lock is not None
    assert lock.name == "test-job"
    assert await _count_locks(lock_repo.session) == 1


async def test_acquire_lock_returns_none_when_lock_held(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """A second acquire while the lock is fresh returns None."""
    first = await lock_repo.acquire("test-job", DEFAULT_INTERVAL_SECONDS)
    assert first is not None

    second = await lock_repo.acquire("test-job", DEFAULT_INTERVAL_SECONDS)
    assert second is None


async def test_acquire_lock_takes_over_stale_lock(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """An existing stale lock is updated and returned to the new caller."""
    stale_time = datetime.now(UTC) - timedelta(seconds=2 * DEFAULT_INTERVAL_SECONDS + 1)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="stale-job",
            owner_token=uuid4(),
            acquired_at=stale_time,
        )
    )
    await lock_repo.session.commit()

    lock = await lock_repo.acquire("stale-job", DEFAULT_INTERVAL_SECONDS)

    assert lock is not None
    assert lock.name == "stale-job"
    assert await _count_locks(lock_repo.session) == 1
    assert lock.acquired_at > stale_time


async def test_acquire_rotates_owner_token_on_stale_takeover(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Taking over a stale lock issues a new owner token.

    Rotating the token is what fences the previous owner. Without it the
    replacement inherits the stale worker's token, and that worker's
    heartbeat would keep refreshing a lock it no longer holds.
    """
    original_token = uuid4()
    stale_time = datetime.now(UTC) - timedelta(seconds=2 * DEFAULT_INTERVAL_SECONDS + 1)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="rotate-job",
            owner_token=original_token,
            acquired_at=stale_time,
        )
    )
    await lock_repo.session.commit()

    taken_over = await lock_repo.acquire("rotate-job", DEFAULT_INTERVAL_SECONDS)

    assert taken_over is not None
    assert taken_over.owner_token != original_token

    stored = await _get_lock(lock_repo.session, "rotate-job")
    assert stored is not None
    assert stored.owner_token == taken_over.owner_token


async def test_stale_owner_cannot_refresh_after_takeover(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """A superseded worker can neither refresh nor release the new lock."""
    original_token = uuid4()
    stale_time = datetime.now(UTC) - timedelta(seconds=2 * DEFAULT_INTERVAL_SECONDS + 1)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="fenced-job",
            owner_token=original_token,
            acquired_at=stale_time,
        )
    )
    await lock_repo.session.commit()

    taken_over = await lock_repo.acquire("fenced-job", DEFAULT_INTERVAL_SECONDS)
    assert taken_over is not None

    # The old worker wakes up and tries to keep its lock alive.
    assert await lock_repo.refresh("fenced-job", original_token) is None

    # It also must not be able to delete the replacement's lock.
    await lock_repo.release("fenced-job", original_token)
    assert await _count_locks(lock_repo.session) == 1

    # The current owner retains full control.
    assert await lock_repo.refresh("fenced-job", taken_over.owner_token) is not None


async def test_acquire_lock_stale_boundary(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Staleness boundary is exactly ``2 * interval_seconds``.

    A lock at the threshold is treated as stale (``<=``), while a lock one
    second fresher than the threshold is not.
    """
    interval = DEFAULT_INTERVAL_SECONDS
    now = datetime.now(UTC)

    at_threshold = now - timedelta(seconds=2 * interval)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="at-threshold-job",
            owner_token=uuid4(),
            acquired_at=at_threshold,
        )
    )
    await lock_repo.session.commit()

    acquired = await lock_repo.acquire("at-threshold-job", interval)
    assert acquired is not None

    fresh_time = now - timedelta(seconds=2 * interval) + timedelta(seconds=1)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="fresh-job",
            owner_token=uuid4(),
            acquired_at=fresh_time,
        )
    )
    await lock_repo.session.commit()

    not_acquired = await lock_repo.acquire("fresh-job", interval)
    assert not_acquired is None


async def test_release_lock_deletes_row(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Releasing a lock removes its row."""
    lock = await lock_repo.acquire("release-job", DEFAULT_INTERVAL_SECONDS)
    assert lock is not None

    await lock_repo.release("release-job", lock.owner_token)

    assert await _count_locks(lock_repo.session) == 0


async def test_refresh_updates_acquired_at(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Refresh bumps acquired_at for an existing lock."""
    lock = await lock_repo.acquire("refresh-job", DEFAULT_INTERVAL_SECONDS)
    assert lock is not None
    original_acquired_at = lock.acquired_at

    await asyncio.sleep(0.01)
    refreshed = await lock_repo.refresh("refresh-job", lock.owner_token)

    assert refreshed is not None
    assert refreshed.acquired_at > original_acquired_at


async def test_refresh_makes_stale_lock_fresh(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Refreshing a stale lock prevents another acquire from stealing it."""
    stale_time = datetime.now(UTC) - timedelta(seconds=2 * DEFAULT_INTERVAL_SECONDS + 1)
    await lock_repo.session.execute(
        insert(BackgroundJobLock).values(
            name="refresh-stale-job",
            owner_token=uuid4(),
            acquired_at=stale_time,
        )
    )
    await lock_repo.session.commit()

    refreshed = await lock_repo.refresh(
        "refresh-stale-job",
        (await _get_lock(lock_repo.session, "refresh-stale-job")).owner_token,
    )
    assert refreshed is not None

    stolen = await lock_repo.acquire("refresh-stale-job", DEFAULT_INTERVAL_SECONDS)
    assert stolen is None


async def test_lock_names_are_independent(
    lock_repo: BackgroundJobLockRepository,
) -> None:
    """Locks for different job names do not interfere with each other."""
    first = await lock_repo.acquire("job-one", DEFAULT_INTERVAL_SECONDS)
    second = await lock_repo.acquire("job-two", DEFAULT_INTERVAL_SECONDS)

    assert first is not None
    assert second is not None
    assert await _count_locks(lock_repo.session) == 2
