"""Database access layer for the ``background_job_lock`` table."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from advanced_alchemy.exceptions import IntegrityError
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from sqlalchemy import delete, update

from fact_inventory.infrastructure.db.models.background_job_lock import (
    BackgroundJobLock,
)

__all__ = ["BackgroundJobLockRepository"]


class BackgroundJobLockRepository(SQLAlchemyAsyncRepository[BackgroundJobLock]):
    """Database access layer for the background_job_lock table.

    Implements a distributed lock with a heartbeat refresh. A lock is
    represented by a single row keyed by job name. Acquisition is atomic:
    either the row does not exist and is inserted, or an existing stale row
    is updated with a new owner token. The unique index on ``name`` is what
    makes this safe under concurrency - two simultaneous inserts cannot both
    succeed, and the loser falls through to the stale-takeover path.

    Every acquisition writes a freshly generated owner token. ``refresh`` and
    ``release`` are conditional on both name and token, so only the current
    owner can keep the lock alive or remove it.
    """

    model_type = BackgroundJobLock

    async def acquire(
        self,
        name: str,
        interval_seconds: int,
    ) -> BackgroundJobLock | None:
        """Attempt to acquire a lock for ``name``.

        A lock is acquired when either:

        - No row for ``name`` exists (one is inserted); or
        - A row exists and its ``acquired_at`` is older than
          ``2 * interval_seconds`` (the stale row is updated with a new token).

        A freshly generated owner token is written on both paths. Rotating the
        token on takeover is what fences the previous owner: its heartbeat
        refreshes and its release are both conditional on the token it was
        handed, so a stalled worker that resumes cannot keep alive or delete
        the lock now held by its replacement.

        Parameters
        ----------
        name : str
            Job name used as the lock key.
        interval_seconds : int
            Configured run interval for the job. Staleness is twice this
            value.

        Returns
        -------
        BackgroundJobLock | None
            The acquired lock, carrying the owner token the caller must use
            for subsequent refresh and release calls, or ``None`` if another
            invocation holds a non-stale lock.
        """
        now = datetime.now(UTC)
        stale_threshold = now - timedelta(seconds=2 * interval_seconds)

        owner_token = uuid4()
        lock = self.model_type(
            name=name,
            owner_token=owner_token,
            acquired_at=now,
        )
        try:
            result = await self.add(lock)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
        else:
            return result

        stmt = (
            update(self.model_type)
            .where(
                self.model_type.name == name,
                self.model_type.acquired_at <= stale_threshold,
            )
            .values(acquired_at=now, owner_token=owner_token)
            .returning(self.model_type)
        )
        update_result = await self.session.execute(stmt)
        await self.session.commit()
        return update_result.scalar_one_or_none()

    async def refresh(self, name: str, owner_token: UUID) -> BackgroundJobLock | None:
        """Refresh ``acquired_at`` for an existing lock.

        Called by the heartbeat while the job is still running. The update is
        conditional on both the job name and owner token. If another worker
        has taken over the lock, ``None`` is returned and the caller should
        treat ownership as lost.

        Parameters
        ----------
        name : str
            Job name used as the lock key.
        owner_token : UUID
            Token of the worker that owns the lock.

        Returns
        -------
        BackgroundJobLock | None
            The refreshed lock, or ``None`` if no row was updated.
        """
        now = datetime.now(UTC)
        stmt = (
            update(self.model_type)
            .where(
                self.model_type.name == name,
                self.model_type.owner_token == owner_token,
            )
            .values(acquired_at=now)
            .returning(self.model_type)
        )
        refresh_result = await self.session.execute(stmt)
        await self.session.commit()
        return refresh_result.scalar_one_or_none()

    async def release(self, name: str, owner_token: UUID) -> None:
        """Release the lock owned by ``owner_token`` for ``name``.

        Parameters
        ----------
        name : str
            Job name used as the lock key.
        owner_token : UUID
            Token of the worker that owns the lock.

        Notes
        -----
        Release failures are logged by the caller. A missing row is not an
        error because the lock may have already been cleaned up.
        """
        stmt = delete(self.model_type).where(
            self.model_type.name == name,
            self.model_type.owner_token == owner_token,
        )
        await self.session.execute(stmt)
        await self.session.commit()
