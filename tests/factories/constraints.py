"""Factory for creating data that tests size constraints."""

import json
from typing import Any

from tests.factories.payloads import create_partial

__all__ = [
    "create_at_limit_field",
    "create_oversized_field",
    "create_payload_over_body_limit",
    "create_payload_under_body_limit",
    "create_payload_with_field_at_limit",
    "create_payload_with_oversized_field",
]

# json.dumps({"data": ""}) == '{"data": ""}' == 12 bytes.
# This is the fixed wrapper overhead when storing a string value in the
# canonical {"data": "<string>"} envelope used by is_valid_size.
JSON_WRAPPER_OVERHEAD: int = len(json.dumps({"data": ""}))


def create_oversized_field(max_mb: int = 4) -> str:
    """Create string exceeding size limit by 1 byte."""
    return "x" * (max_mb * 1024 * 1024 + 1)


def create_at_limit_field(max_mb: int = 4) -> str:
    """Create string whose JSON encoding lands exactly at the size limit.

    The field is always stored as {"data": "<string>"}.  The empty-value
    form of that dict, json.dumps({"data": ""}), is exactly 12 bytes
    (JSON_WRAPPER_OVERHEAD).  Subtracting that overhead makes the total
    encoded length equal max_mb MiB, satisfying the <= check in is_valid_size.
    """
    return "x" * (max_mb * 1024 * 1024 - JSON_WRAPPER_OVERHEAD)


def create_payload_with_oversized_field(
    max_field_mb: int = 4,
    field: str = "system_facts",
) -> dict[str, Any]:
    """Create HTTP payload with one fact field exceeding JSON size limit.

    Delegates dict shape to create_partial.
    Raises ValueError if field is not a valid fact field name (via create_partial).
    """
    oversized_data = {"data": create_oversized_field(max_field_mb)}
    return create_partial(field, oversized_data)


def create_payload_with_field_at_limit(max_field_mb: int = 4) -> dict[str, Any]:
    """Create HTTP payload with system_facts exactly at JSON size limit."""
    return create_partial(
        "system_facts",
        {"data": create_at_limit_field(max_field_mb)},
    )


def create_payload_under_body_limit(max_body_mb: int) -> dict[str, Any]:
    """Create HTTP payload well under HTTP body limit (10% of max)."""
    safe_data = "x" * ((max_body_mb * 1024 * 1024) // 10)
    return create_partial("system_facts", {"data": safe_data})


def create_payload_over_body_limit(max_body_mb: int) -> dict[str, Any]:
    """Create HTTP payload exceeding HTTP body limit (2x max)."""
    oversized_data = "x" * (max_body_mb * 1024 * 1024 * 2)
    return create_partial("system_facts", {"data": oversized_data})
