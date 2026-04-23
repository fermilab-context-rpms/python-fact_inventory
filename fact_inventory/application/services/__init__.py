"""Service layer for fact inventory operations.

The service layer implements application rules and business logic for fact
inventory operations. Services express application-level behavior while
delegating database operations to the repository layer.

Service Layer Rationale
-----------------------
Services embody application rules: validation, state transitions, retention
policies, and orchestration. They use domain objects to express business rules
and call repositories for database work. This separation lets rules evolve
independently - retention policy changes affect only services, not controllers
or database schemas.

This module re-exports from submodules for cleaner organization.

This layer has no HTTP or framework imports. All exceptions raised here are
plain Python exceptions; the presentation layer converts them to HTTP responses.
"""

from fact_inventory.application.services.fact import FactInventoryService

__all__ = ["FactInventoryService"]
