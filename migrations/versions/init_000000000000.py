"""Initial schema: fact_inventory and background_job_lock tables.

Revision ID: 000000000000
Revises:

Creates the base table schema:

- ``fact_inventory``: append-only fact history, HASH partitioned on
  client_address across NUM_PARTITIONS partitions (PostgreSQL only), with
  BRIN, GIN and btree indexes and per-partition storage tuning.
- ``background_job_lock``: distributed lock rows for background jobs.

The experimental CMDB views live in revision 000000000001 so they can be
cycled without touching these tables.

All PostgreSQL-only behavior is dialect-gated so this file also produces a
usable (unpartitioned, untuned) schema on SQLite for local and test use.
"""

import sqlalchemy as sa
from advanced_alchemy.types import DateTimeUTC, JsonB, guid
from alembic import op
from sqlalchemy.dialects import postgresql

__all__ = [
    "downgrade",
    "upgrade",
]

# Revision identifiers, used by Alembic.
revision = "000000000000"
down_revision = None
branch_labels = None
depends_on = None

# --- Partitioning configuration (PostgreSQL only) --------------------------

NUM_PARTITIONS = 64

# Storage tuning applied to each partition. A partitioned parent table cannot
# carry storage parameters, so these are set per partition at creation time.
# The low fillfactor leaves free space per page for HOT updates; the
# aggressive autovacuum thresholds keep dead tuples (from JSONB column
# updates) from accumulating between vacuum runs.
PARTITION_FILLFACTOR = 75
PARTITION_AUTOVACUUM_VACUUM_SCALE_FACTOR = 0.01
PARTITION_AUTOVACUUM_VACUUM_THRESHOLD = 1000


def _is_postgresql() -> bool:
    """Return True when running against PostgreSQL."""
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    """Create tables, partitions, and indexes."""
    _create_fact_inventory()
    _create_fact_inventory_indexes()
    _create_background_job_lock()


def downgrade() -> None:
    """Drop both tables.

    Indexes are dropped implicitly with their table, and partitions are
    dropped implicitly (CASCADE) with the partitioned parent, so neither
    needs separate cleanup.
    """
    op.drop_table("background_job_lock")
    op.drop_table("fact_inventory")


# --- fact_inventory ---------------------------------------------------------


def _create_fact_inventory() -> None:
    """Create the fact_inventory table with a composite primary key.

    On PostgreSQL, postgresql_partition_by makes this a partitioned parent;
    actual partitions are created by _create_partitions. On other dialects
    the option is silently ignored and this produces a normal table.

    PostgreSQL requires the partition key (client_address) to be part of any
    primary key on a partitioned table, so the PK is composite:
    (id, client_address). id (GUID) carries practical uniqueness;
    client_address is folded in only to satisfy the partitioning rule. The
    PrimaryKeyConstraint marks both columns NOT NULL on its own.
    """
    op.create_table(
        "fact_inventory",
        sa.Column("id", guid.GUID(length=16), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            DateTimeUTC(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            DateTimeUTC(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "client_address",
            sa.String(length=45).with_variant(postgresql.INET(), "postgresql"),
            nullable=False,
            comment="Client IP address (IPv4 or IPv6)",
        ),
        sa.Column(
            "system_facts",
            JsonB,
            server_default=sa.text("'{}'"),
            nullable=False,
            comment="System facts as JSON",
        ),
        sa.Column(
            "package_facts",
            JsonB,
            server_default=sa.text("'{}'"),
            nullable=False,
            comment="Package facts as JSON",
        ),
        sa.Column(
            "local_facts",
            JsonB,
            server_default=sa.text("'{}'"),
            nullable=False,
            comment="Local facts as JSON",
        ),
        sa.Column(
            "client_facts",
            JsonB,
            server_default=sa.text("'{}'"),
            nullable=False,
            comment="Agent facts as JSON",
        ),
        sa.PrimaryKeyConstraint("id", "client_address", name=op.f("pk_fact_inventory")),
        postgresql_partition_by="HASH (client_address)",
    )

    if _is_postgresql():
        _create_partitions()


def _partition_name(partition_index: int) -> str:
    """Return the physical table name for hash partition N.

    Centralized so partition creation and any future partition maintenance
    cannot drift out of sync on naming.
    """
    return f"fact_inventory_p{partition_index:02d}"


def _create_partitions() -> None:
    """Create the NUM_PARTITIONS HASH partitions. Caller must check dialect.

    Storage parameters are set in the same statement that creates the
    partition, so each partition costs one round trip rather than two.
    """
    for partition_index in range(NUM_PARTITIONS):
        op.execute(
            f"""
            CREATE TABLE {_partition_name(partition_index)}
            PARTITION OF fact_inventory
            FOR VALUES WITH (MODULUS {NUM_PARTITIONS}, REMAINDER {partition_index})
            WITH (
                fillfactor = {PARTITION_FILLFACTOR},
                autovacuum_vacuum_scale_factor =
                    {PARTITION_AUTOVACUUM_VACUUM_SCALE_FACTOR},
                autovacuum_vacuum_threshold =
                    {PARTITION_AUTOVACUUM_VACUUM_THRESHOLD}
            )
            """
        )


def _create_fact_inventory_indexes() -> None:
    """Create fact_inventory indexes.

    On PostgreSQL, BRIN and GIN indexes provide optimizations for time-series
    and JSON queries respectively. On SQLite the postgresql_using options are
    silently ignored and standard btree indexes are created instead.
    """
    # Standard btree indexes
    op.create_index(
        "ix_fact_inventory_client_address",
        "fact_inventory",
        ["client_address"],
    )
    op.create_index(
        "ix_fact_inventory_updated_at",
        "fact_inventory",
        ["updated_at"],
    )
    # Serves the history-retention window function, which partitions by
    # client_address and orders by updated_at.
    op.create_index(
        "ix_fact_inventory_client_address_updated_at",
        "fact_inventory",
        ["client_address", "updated_at"],
    )
    # BRIN index on created_at for linear time-series data.
    op.create_index(
        "ix_fact_inventory_created_at",
        "fact_inventory",
        ["created_at"],
        postgresql_using="brin",
    )
    # GIN indexes on JSON columns for efficient containment/selection queries.
    for column in ("system_facts", "package_facts", "local_facts", "client_facts"):
        op.create_index(
            f"ix_fact_inventory_{column}",
            "fact_inventory",
            [column],
            postgresql_using="gin",
        )


# --- background_job_lock ----------------------------------------------------


def _create_background_job_lock() -> None:
    """Create the background_job_lock table and its indexes.

    Background jobs use this table as a distributed lock: a job inserts a row
    before starting and deletes it when finished. The unique index on ``name``
    is what makes acquisition atomic - concurrent inserts cannot both succeed.
    ``acquired_at`` is refreshed by a heartbeat while the job runs so that
    long-running jobs are not mistaken for stale locks.
    """
    op.create_table(
        "background_job_lock",
        sa.Column("id", guid.GUID(length=16), nullable=False),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column(
            "acquired_at",
            DateTimeUTC(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="UTC timestamp of the most recent acquisition or heartbeat",
        ),
        sa.Column(
            "owner_token",
            guid.GUID(length=16),
            nullable=False,
            comment="Unique token identifying the current lock owner",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
            comment="Unique job name used as the lock key",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_background_job_lock")),
    )
    op.create_index(
        "ix_background_job_lock_name",
        "background_job_lock",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_background_job_lock_acquired_at",
        "background_job_lock",
        ["acquired_at"],
    )
