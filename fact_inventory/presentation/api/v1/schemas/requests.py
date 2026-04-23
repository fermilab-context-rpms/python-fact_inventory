"""Request models for API endpoints.

Defines typed request bodies used by the v1 API. Keeping these separate from
the ORM models lets the HTTP contract evolve independently of the database
schema.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

__all__ = ["FactInventoryCreateRequest"]


class FactInventoryCreateRequest(BaseModel):
    """Request body for POST /api/v1/facts.

    All fact categories are required. At least one category must contain data;
    that rule is enforced by the service layer so the error type remains
    framework-agnostic.
    """

    model_config = ConfigDict(extra="forbid")

    system_facts: dict[str, Any]
    package_facts: dict[str, Any]
    local_facts: dict[str, Any]
    client_facts: dict[str, Any]
