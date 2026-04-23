"""Database model for the ``fact_inventory`` table.

This module defines the ORM entity layer. Models map database tables to Python
classes and handle schema definition. They do not contain business logic - that
belongs in services. This separation allows the schema to remain stable while
application rules evolve independently.
"""

from typing import Any

from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.types import JsonB
from sqlalchemy import Index, PrimaryKeyConstraint, String, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["FactInventory"]


class FactInventory(UUIDAuditBase):
    """ORM model for the fact_inventory table.

    Stores one record per connecting client IP address. The JSON columns
    hold arbitrary data submitted by the client (for example Ansible
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
    agent_facts : dict[str, Any]
        Local facts as JSON. Default: {}.

    Notes
    -----
    Database state is managed by Litestar's Alembic integration.
    """

    __tablename__ = "fact_inventory"

    client_address: Mapped[str] = mapped_column(
        String(45).with_variant(INET, "postgresql"),
        nullable=False,
        primary_key=True,
        comment="Client IP address (IPv4 or IPv6)",
    )

    system_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        nullable=False,
        comment="System facts as JSON",
    )

    package_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        nullable=False,
        comment="Package facts as JSON",
    )

    local_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        nullable=False,
        comment="Local facts as JSON",
    )
    agent_facts: Mapped[dict[str, Any]] = mapped_column(
        JsonB,
        server_default=text("'{}'"),
        nullable=False,
        comment="Agent facts as JSON",
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", "client_address"),
        Index(
            "ix_fact_inventory_created_at",
            "created_at",
            postgresql_using="brin",
        ),
        Index(
            "ix_fact_inventory_updated_at",
            "updated_at",
        ),
        Index(
            "ix_fact_inventory_client_address",
            "client_address",
        ),
        # PostgreSQL: GIN indexes for efficient JSON querying
        Index("ix_fact_inventory_system_facts", "system_facts", postgresql_using="gin"),
        Index(
            "ix_fact_inventory_package_facts", "package_facts", postgresql_using="gin"
        ),
        Index("ix_fact_inventory_local_facts", "local_facts", postgresql_using="gin"),
        Index("ix_fact_inventory_agent_facts", "agent_facts", postgresql_using="gin"),
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
