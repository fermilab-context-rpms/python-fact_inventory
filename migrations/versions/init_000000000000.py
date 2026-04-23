"""Initial schema: fact_inventory table with indexes and PostgreSQL optimizations.

Revision ID: 000000000000
Revises:

Creates the core fact_inventory table with:
- UUID primary key
- Audit timestamps (created_at, updated_at)
- JSONB columns for system_facts, package_facts, local_facts
- INET type for client_address (PostgreSQL-specific)
- HASH partitioning on client_address with NUM_PARTITIONS partitions (PostgreSQL only)
- GIN indexes for efficient JSON queries
- BRIN index on created_at for time-series optimization
- PostgreSQL-specific tuning: fillfactor, autovacuum settings for large JSONB columns

All PostgreSQL-only behavior is dialect-gated so this file also produces a
usable (unpartitioned, untuned) table on SQLite for local/test use.
"""

import sqlalchemy as sa
from advanced_alchemy.types import DateTimeUTC, JsonB, guid
from alembic import op
from sqlalchemy.dialects import postgresql

__all__ = [
    "downgrade",
    "upgrade",
]

# alembic autogenerate renders this custom type with an "sa." prefix.
# Attach it to the sa namespace so that rendering resolves without a
# separate import line in every generated migration.
sa.DateTimeUTC = DateTimeUTC

# Revision identifiers, used by Alembic.
revision = "000000000000"
down_revision = None
branch_labels = None
depends_on = None

# --- Partitioning configuration (PostgreSQL only) --------------------------

NUM_PARTITIONS = 64
TABLE_NAME = "fact_inventory"

# Storage tuning applied to each partition; see _tune_partition_storage.
# Low fillfactor leaves free space per page for HOT updates; the
# aggressive autovacuum thresholds keep dead tuples (from JSONB column
# updates) from accumulating between vacuum runs.
PARTITION_FILLFACTOR = 75
PARTITION_AUTOVACUUM_VACUUM_SCALE_FACTOR = 0.01
PARTITION_AUTOVACUUM_VACUUM_THRESHOLD = 1000


def upgrade() -> None:
    """Create fact_inventory: table, partitions, indexes, storage tuning."""
    _create_table()

    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        _create_partitions()

    _create_indexes()


def downgrade() -> None:
    """Drop fact_inventory and all its indexes.

    Partitions are dropped implicitly (CASCADE) when the partitioned
    parent table is dropped, so no separate partition cleanup is needed.
    """
    _drop_indexes()
    op.drop_table(TABLE_NAME)


# --- Table -----------------------------------------------------------


def _create_table() -> None:
    """Create the fact_inventory table with columns and composite primary key.

    On PostgreSQL, postgresql_partition_by makes this a partitioned parent;
    actual partitions are created by _create_partitions. On other dialects,
    the option is silently ignored and this produces a normal table.

    PostgreSQL requires the partition key (client_address) to be part of
    any primary key on a partitioned table, so the PK is composite:
    (id, client_address). id (GUID) carries practical uniqueness;
    client_address is folded in only to satisfy the partitioning rule.
    Both are marked primary_key=True on the column AND listed in the
    explicit PrimaryKeyConstraint so the two declarations agree exactly,
    avoiding SQLAlchemy warnings on table creation.
    """
    op.create_table(
        TABLE_NAME,
        sa.Column("id", guid.GUID(length=16), nullable=False, primary_key=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTimeUTC(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTimeUTC(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "client_address",
            sa.String(length=45).with_variant(postgresql.INET(), "postgresql"),
            nullable=False,
            primary_key=True,
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
            "agent_facts",
            JsonB,
            server_default=sa.text("'{}'"),
            nullable=False,
            comment="Agent facts as JSON",
        ),
        sa.PrimaryKeyConstraint("id", "client_address", name=op.f(f"pk_{TABLE_NAME}")),
        postgresql_partition_by="HASH (client_address)",
    )


# --- Partitions (PostgreSQL only) ---------------------------------------


def _partition_name(partition_index: int) -> str:
    """Return the physical table name for hash partition N.

    Centralized so partition creation and partition storage tuning
    cannot drift out of sync on naming.
    """
    return f"{TABLE_NAME}_p{partition_index:02d}"


def _create_partitions() -> None:
    """Create the NUM_PARTITIONS HASH partitions. Caller must check dialect."""
    for partition_index in range(NUM_PARTITIONS):
        op.execute(
            sa.text(
                f"""
                CREATE TABLE {_partition_name(partition_index)}
                PARTITION OF {TABLE_NAME}
                FOR VALUES WITH (MODULUS {NUM_PARTITIONS}, REMAINDER {partition_index})
                """
            )
        )
        _tune_partition_storage(partition_index)


def _tune_partition_storage(partition_index: int) -> None:
    """Apply storage tuning to each partition.

    A partitioned parent table cannot carry storage parameters directly;
    each partition must be tuned individually.
    """
    op.execute(
        sa.text(
            f"""
                ALTER TABLE {_partition_name(partition_index)}
                SET (
                    fillfactor = {PARTITION_FILLFACTOR},
                    autovacuum_vacuum_scale_factor =
                        {PARTITION_AUTOVACUUM_VACUUM_SCALE_FACTOR},
                    autovacuum_vacuum_threshold =
                        {PARTITION_AUTOVACUUM_VACUUM_THRESHOLD}
                )
                """
        )
    )


# --- Indexes ----------------------------------------------------------


def _create_indexes() -> None:
    """Create indexes: btree on timestamps/composites, BRIN/GIN on JSON.

    On PostgreSQL, BRIN and GIN indexes provide optimizations for
    time-series and JSON queries respectively. On SQLite, these
    postgresql_using options are silently ignored, and standard
    btree indexes are created instead.
    """
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        # Standard btree indexes
        batch_op.create_index(f"ix_{TABLE_NAME}_updated_at", ["updated_at"])

        batch_op.create_index(f"ix_{TABLE_NAME}_client_address", ["client_address"])

        # BRIN index on created_at for linear time-series
        batch_op.create_index(
            f"ix_{TABLE_NAME}_created_at",
            ["created_at"],
            postgresql_using="brin",
        )

        # GIN indexes on JSON columns for efficient containment/selection queries
        batch_op.create_index(
            f"ix_{TABLE_NAME}_system_facts",
            ["system_facts"],
            postgresql_using="gin",
        )
        batch_op.create_index(
            f"ix_{TABLE_NAME}_package_facts",
            ["package_facts"],
            postgresql_using="gin",
        )
        batch_op.create_index(
            f"ix_{TABLE_NAME}_local_facts",
            ["local_facts"],
            postgresql_using="gin",
        )
        batch_op.create_index(
            f"ix_{TABLE_NAME}_agent_facts",
            ["agent_facts"],
            postgresql_using="gin",
        )


def _drop_indexes() -> None:
    """Drop all indexes."""
    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        batch_op.drop_index(f"ix_{TABLE_NAME}_client_address")
        batch_op.drop_index(f"ix_{TABLE_NAME}_updated_at")
        batch_op.drop_index(f"ix_{TABLE_NAME}_created_at")
        batch_op.drop_index(f"ix_{TABLE_NAME}_system_facts")
        batch_op.drop_index(f"ix_{TABLE_NAME}_package_facts")
        batch_op.drop_index(f"ix_{TABLE_NAME}_local_facts")
        batch_op.drop_index(f"ix_{TABLE_NAME}_agent_facts")
