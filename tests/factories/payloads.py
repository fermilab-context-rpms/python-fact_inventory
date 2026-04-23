"""Factory for creating fact record payloads (dict format)."""

from typing import Any

__all__ = [
    "FACT_FIELDS",
    "create_categories",
    "create_empty",
    "create_minimal",
    "create_partial",
    "create_record",
    "create_valid",
]

FACT_FIELDS = (
    "system_facts",
    "package_facts",
    "local_facts",
    "client_facts",
)


def create_empty() -> dict[str, Any]:
    """Create a payload with all fact categories present and empty."""
    payload: dict[str, Any] = {}
    for field in FACT_FIELDS:
        payload[field] = {}
    return payload


def create_categories(
    *,
    system_facts: dict[str, Any] | None = None,
    package_facts: dict[str, Any] | None = None,
    local_facts: dict[str, Any] | None = None,
    client_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a payload with explicit fact category values."""
    payload = create_empty()
    if system_facts is not None:
        payload["system_facts"] = system_facts
    if package_facts is not None:
        payload["package_facts"] = package_facts
    if local_facts is not None:
        payload["local_facts"] = local_facts
    if client_facts is not None:
        payload["client_facts"] = client_facts
    return payload


def create_record(
    client_address: str,
    *,
    system_facts: dict[str, Any] | None = None,
    package_facts: dict[str, Any] | None = None,
    local_facts: dict[str, Any] | None = None,
    client_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a service/repository payload including client_address."""
    payload = create_categories(
        system_facts=system_facts,
        package_facts=package_facts,
        local_facts=local_facts,
        client_facts=client_facts,
    )
    payload["client_address"] = client_address
    return payload


def create_valid() -> dict[str, Any]:
    """Create valid payload with all fact categories populated (no client_address)."""
    return create_categories(
        system_facts={"os": "RHEL", "version": "9"},
        package_facts={"curl": "7.68.0"},
        local_facts={"custom_key": "custom_value"},
        client_facts={"target_url": "/example/path"},
    )


def create_minimal() -> dict[str, Any]:
    """Create minimal HTTP-safe payload for tests where content is irrelevant.

    Delegates to create_partial so the dict structure is defined in one place.
    Use this when any valid payload will do (routing, error handling, method checks).
    Use create_partial() when the specific category or data matters to the test.
    """
    return create_partial("system_facts", {"os": "RHEL"})


def create_partial(
    fact_type: str,
    fact_data: dict[str, Any],
) -> dict[str, Any]:
    """Create HTTP-safe payload with only one fact category populated.

    Does not include client_address: HTTP endpoints derive the client
    address from the TCP connection, not the request body. Callers
    that need client_address for service-layer tests should add it
    to the returned dict themselves.

    Raises ValueError if fact_type not in {system_facts, package_facts, local_facts, client_facts}.
    """
    if fact_type not in FACT_FIELDS:
        msg = f"Invalid fact_type: {fact_type}"
        raise ValueError(msg)

    payload = create_empty()
    payload[fact_type] = fact_data
    return payload
