"""Domain layer for fact inventory.

This directory contains business rules, constraints, and domain models
that express application logic independently of framework or database
implementation details.

Structure
---------
- validation/: Payload validation rules (size limits, requirements)
- retention/: Data retention policies (time-based and history-based)

Design Philosophy
-----------------
Domain objects should:
- Be free of framework imports (no Litestar, SQLAlchemy, etc.)
- Express business rules as pure Python classes/functions
- Raise domain-specific exceptions (converted to HTTP errors elsewhere)
- Be testable without mocking infrastructure
- Support reuse across services and API versions

See each subdirectory for detailed documentation.

"""
