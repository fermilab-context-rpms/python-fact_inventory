"""Tests for JSONFieldSizeConstraint domain object.

Tests verify field size validation, boundary checking, and fact requirement
validation across various payload configurations. This domain object enforces
safety constraints to prevent database bloat and oversized requests.

Design Notes:
- Size constraints are in MB for operator readability (not bytes)
- Boundary testing includes min/max/off-by-one cases
- Fact requirements enforce at least one non-empty category
- Error messages include field names and limits for debugging
"""

import json

import pytest

from fact_inventory.domain.constraints import JSONFieldSizeConstraint
from fact_inventory.lib.exceptions import FactValidationError

ONE_MB_LIMIT = 1.0
SMALL_LIMIT_MB = 0.001
STANDARD_LIMIT_MB = 5.0


def build_constraint(max_size_mb: float = STANDARD_LIMIT_MB) -> JSONFieldSizeConstraint:
    """Create a JSONFieldSizeConstraint with a clear default limit."""
    return JSONFieldSizeConstraint(max_size_mb=max_size_mb)


def test_json_field_size_constraint_validation_bounds() -> None:
    """Constructor validates max_size_mb is strictly positive."""
    # Positive value: accepted
    build_constraint(SMALL_LIMIT_MB)

    # Zero: rejected
    with pytest.raises(ValueError):
        JSONFieldSizeConstraint(max_size_mb=0)

    # Negative: rejected
    with pytest.raises(ValueError):
        JSONFieldSizeConstraint(max_size_mb=-1.0)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        # 1 byte under the 1 MB limit: json.dumps({"k": "x"*N}) = N+9 bytes;
        # N=1_048_566 yields 1_048_575 bytes (limit is 1_048_576).
        {"k": "x" * 1_048_566},
    ],
)
def test_json_field_size_constraint_is_valid_size_under_limit(payload: dict) -> None:
    """Payloads under size limit return True."""
    c = build_constraint(ONE_MB_LIMIT)
    assert c.is_valid_size(json.dumps(payload).encode()) is True


def test_json_field_size_constraint_is_valid_size_over_limit() -> None:
    """Payloads exceeding limit return False."""
    c = build_constraint(SMALL_LIMIT_MB)
    assert c.is_valid_size(json.dumps({"k": "x" * 10000}).encode()) is False


@pytest.mark.parametrize(
    "payload",
    [
        {"os": "RHEL"},
        {},
    ],
)
def test_json_field_size_constraint_validate_size(payload: dict) -> None:
    """validate_size succeeds for valid payloads."""
    build_constraint().validate_size("field", payload)


def test_json_field_size_constraint_validate_size_oversized_raises() -> None:
    """validate_size raises ValueError for oversized payloads."""
    c = build_constraint(SMALL_LIMIT_MB)
    with pytest.raises(ValueError):
        c.validate_size("large_field", {"x": "y" * 2000})


def test_json_field_size_constraint_instances_are_independent() -> None:
    """Separate instances maintain independent limits."""
    c1 = build_constraint(ONE_MB_LIMIT)
    c2 = build_constraint(10.0)
    # ~2 MB payload: json.dumps({"x": "y"*2_000_000}) is ~2_000_009 bytes
    large = json.dumps({"x": "y" * 2_000_000}).encode()
    assert c1.is_valid_size(large) is False, "c1 (1 MB) should reject ~2 MB payload"
    assert c2.is_valid_size(large) is True, "c2 (10 MB) should accept ~2 MB payload"


def test_json_field_size_constraint_has_required_facts_with_data() -> None:
    """has_required_facts passes when at least one fact type has data."""
    c = build_constraint()
    c.has_required_facts({"system_facts": {"os": "RHEL"}})


def test_json_field_size_constraint_has_required_facts_rejects_empty() -> None:
    """has_required_facts raises when all fact types are empty."""
    c = build_constraint()
    with pytest.raises(FactValidationError):
        c.has_required_facts(
            {"system_facts": {}, "package_facts": {}, "local_facts": {}}
        )


def test_json_field_size_constraint_has_required_facts_accepts_any_non_empty() -> None:
    """has_required_facts accepts any non-empty fact type."""
    c = build_constraint()
    c.has_required_facts(
        {"system_facts": {}, "package_facts": {"glibc": "2.36"}, "local_facts": {}}
    )


def test_json_field_size_constraint_validate_json_fields_success() -> None:
    """validate_json_fields passes for valid mixed payloads."""
    c = build_constraint()
    c.validate_json_fields(
        {
            "system_facts": {"os": "RHEL"},
            "package_facts": {"glibc": "2.36"},
            "local_facts": {},
        }
    )


def test_json_field_size_constraint_validate_json_fields_rejects_empty() -> None:
    """validate_json_fields raises when all facts are empty."""
    c = build_constraint()
    with pytest.raises(FactValidationError):
        c.validate_json_fields(
            {"system_facts": {}, "package_facts": {}, "local_facts": {}}
        )


def test_json_field_size_constraint_validate_json_fields_rejects_oversized() -> None:
    """validate_json_fields raises when any field exceeds limit."""
    c = build_constraint(SMALL_LIMIT_MB)
    with pytest.raises(ValueError):
        c.validate_json_fields(
            {
                "system_facts": {"os": "RHEL"},
                "package_facts": {"x": "y" * 2000},
                "local_facts": {},
            }
        )


def test_fact_validation_error_is_subclass_of_value_error() -> None:
    """FactValidationError inherits from ValueError."""
    assert issubclass(FactValidationError, ValueError)
