"""Database model for the ``fact_inventory`` table."""

from typing import Any

from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.types import JsonB
from sqlalchemy import Index, String, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["FactInventory"]


class FactInventory(UUIDAuditBase):
    """ORM model for the fact_inventory table.

    Append-only fact history. Each submission inserts a new row, so a single
    ``client_address`` accumulates many rows over time. Old rows are removed
    by the retention background jobs, not by overwriting in place. The JSON
    columns hold arbitrary data submitted by the client (for example Ansible
    setup facts).

    Attributes
    ----------
    client_address : str
        Client IP address (IPv4 or IPv6).
    system_facts : dict[str, Any]
        System facts as JSON. Default: {}.
    package_facts : dict[str, Any]
        Package facts as JSON. Default: {}.
    local_facts : dict[str, Any]
        Local facts as JSON. Default: {}.
    client_facts : dict[str, Any]
        Agent facts as JSON. Default: {}.

    Notes
    -----
    The primary key is composite, ``(id, client_address)``. PostgreSQL
    requires the partition key to be part of any primary key on a
    partitioned table, and this table is HASH partitioned on
    ``client_address``. Practical uniqueness is carried by ``id`` alone;
    ``client_address`` is folded in only to satisfy that rule.

    Column types are stated explicitly rather than left to the declarative
    type_annotation_map. The mapping would resolve ``dict[str, Any]`` to the
    same ``JsonB`` instance, but spelling it out keeps the storage type
    visible at the column and independent of the base class configuration.
    ``JsonB`` is ``sqlalchemy.JSON`` with dialect variants attached, so it
    renders as JSONB on PostgreSQL and JSON elsewhere.

    Database state is managed by Litestar's Alembic integration.
    """

    __tablename__ = "fact_inventory"

    client_address: Mapped[str] = mapped_column(
        String(45).with_variant(INET, "postgresql"),
        primary_key=True,
        index=True,
        comment="Client IP address (IPv4 or IPv6)",
    )

    system_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        comment="System facts as JSON",
    )

    package_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        comment="Package facts as JSON",
    )

    local_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        comment="Local facts as JSON",
    )

    client_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        comment="Agent facts as JSON",
    )

    # Only indexes with no column-level equivalent are declared here.
    # Single-column btree indexes are declared via ``index=True`` above.
    __table_args__ = (
        # created_at comes from our base model
        # BRIN suits the append-only, monotonically increasing created_at.
        Index(
            "ix_fact_inventory_created_at",
            "created_at",
            postgresql_using="brin",
        ),
        # updated_at comes from our base model
        Index("ix_fact_inventory_updated_at", "updated_at"),
        # Serves the history-retention window function, which partitions by
        # client_address and orders by updated_at. Must be named explicitly:
        # the ix_%(column_0_label)s convention would otherwise collide with
        # the single-column client_address index.
        Index(
            "ix_fact_inventory_client_address_updated_at",
            "client_address",
            "updated_at",
        ),
        # PostgreSQL: GIN indexes for efficient JSON querying
        Index("ix_fact_inventory_system_facts", "system_facts", postgresql_using="gin"),
        Index(
            "ix_fact_inventory_package_facts", "package_facts", postgresql_using="gin"
        ),
        Index("ix_fact_inventory_local_facts", "local_facts", postgresql_using="gin"),
        Index("ix_fact_inventory_client_facts", "client_facts", postgresql_using="gin"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        """Return string representation with key attributes.

        Returns
        -------
        str
            Formatted string showing client_address, created_at, and updated_at.
        """
        return (
            f"<FactInventory client_address={self.client_address}"
            f" created_at={self.created_at}"
            f" updated_at={self.updated_at}>"
        )
