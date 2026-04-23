"""JSON payload requirements validation domain object.

Domain object expressing payload requirements independently of the HTTP
layer. No framework imports.

Notes
-----
    JsonPayloadRequirementsValidator is a domain rule, not an HTTP concern.
    Raising a domain exception here keeps the domain free of litestar/pydantic
    deps; the service layer or presentation layer is responsible for converting
    the error to the appropriate HTTP response.
"""

from typing import Any

from fact_inventory.lib.exceptions import FactValidationError

__all__ = ["JsonPayloadRequirementsValidator"]


class JsonPayloadRequirementsValidator:
    """Validates that JSON payloads meet minimum requirements.

    Ensures at least one fact category contains data.
    """

    JSON_FIELD_NAMES_NEED_ONE_OF = (
        "system_facts",
        "package_facts",
        "local_facts",
        "client_facts",
    )

    def has_required_facts(self, data: dict[str, Any]) -> None:
        """Validate that at least one fact category contains data.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing facts

        Raises
        ------
        FactValidationError
            If all fact categories are empty or missing.
        """
        if not any(data.get(field) for field in self.JSON_FIELD_NAMES_NEED_ONE_OF):
            raise FactValidationError(  # noqa: TRY003
                "At least one fact category must contain data"
            )
