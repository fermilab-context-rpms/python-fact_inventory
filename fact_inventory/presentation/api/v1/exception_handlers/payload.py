"""Handler for FactPayloadTooLargeError."""

from typing import Any

from litestar import Response
from litestar.status_codes import HTTP_413_REQUEST_ENTITY_TOO_LARGE

from fact_inventory.lib.exceptions import FactPayloadTooLargeError
from fact_inventory.presentation.api.v1.exception_handlers.helpers import (
    _client_address,
    _error_response,
)

__all__ = ["fact_payload_too_large_error_handler"]


def fact_payload_too_large_error_handler(
    request: Any,
    exc: FactPayloadTooLargeError,
) -> Response[dict[str, Any]]:
    """Map oversized JSON field failures to HTTP 413."""
    request.logger.warning(
        "Fact payload too large",
        client_address=_client_address(request),
        error=str(exc),
    )
    return _error_response(
        "Request entity too large", HTTP_413_REQUEST_ENTITY_TOO_LARGE
    )
