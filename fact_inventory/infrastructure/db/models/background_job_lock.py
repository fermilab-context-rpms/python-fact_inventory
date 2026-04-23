"""Database model for the ``background_job_lock`` table."""

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import UUIDBase
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["BackgroundJobLock"]


class BackgroundJobLock(UUIDBase):
    """ORM model for the background_job_lock table.

    Provides a distributed lock for background jobs. A job inserts a row with
    a unique owner token before starting work and deletes it when finished.
    The ``acquired_at`` column is refreshed periodically by a heartbeat while
    the job is still running. Other invocations skip if a non-stale row exists.

    Attributes
    ----------
    acquired_at : datetime
        UTC timestamp of the most recent acquisition or heartbeat refresh.
    owner_token : UUID
        Token identifying the worker that currently owns the lock. Compared
        for equality by ``refresh``/``release`` to fence out a previous owner;
        it carries no uniqueness constraint.
    name : str
        Unique job name (lock key).

    Notes
    -----
    Staleness is determined by the caller using the configured job interval.
    A lock is considered stale when ``acquired_at`` is older than twice the
    job's run interval.

    Taking over a stale lock rotates ``owner_token``. Refresh and release are
    both conditional on the token, so a stalled worker that resumes after its
    lock was taken over cannot refresh or delete the replacement worker's
    lock; its next heartbeat fails and it stands down.
    """

    __tablename__ = "background_job_lock"

    acquired_at: Mapped[datetime] = mapped_column(
        index=True,
        server_default=func.now(),
        comment="UTC timestamp of the most recent acquisition or heartbeat",
    )
    owner_token: Mapped[UUID] = mapped_column(
        comment="Token identifying the current lock owner",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        comment="Unique job name used as the lock key",
    )

    def __repr__(self) -> str:  # pragma: no cover
        """Return string representation with key attributes.

        Returns
        -------
        str
            Formatted string showing name and acquired_at.
        """
        return f"<BackgroundJobLock name={self.name} acquired_at={self.acquired_at}>"
