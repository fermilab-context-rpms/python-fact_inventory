"""Handler for FactValidationError."""

from typing import Any

from litestar import Response
from litestar.status_codes import HTTP_400_BAD_REQUEST

from fact_inventory.lib.exceptions import FactValidationError
from fact_inventory.presentation.api.v1.exception_handlers.helpers import (
    _client_address,
    _error_response,
)

__all__ = ["fact_validation_error_handler"]


def fact_validation_error_handler(
    request: Any,
    exc: FactValidationError,
) -> Response[dict[str, Any]]:
    """Map business validation failures to HTTP 400."""
    request.logger.warning(
        "Fact validation failed",
        client_address=_client_address(request),
        error=str(exc),
    )
    return _error_response("Validation failed", HTTP_400_BAD_REQUEST)
