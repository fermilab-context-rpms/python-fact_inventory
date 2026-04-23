"""Handlers for SQLAlchemy and advanced-alchemy errors."""

from typing import Any

from litestar import Response
from litestar.status_codes import (
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from fact_inventory.presentation.api.v1.exception_handlers.helpers import (
    _client_address,
    _error_response,
)

__all__ = ["sqlalchemy_error_handler"]


def sqlalchemy_error_handler(
    request: Any,
    exc: SQLAlchemyError,
) -> Response[dict[str, Any]]:
    """Map database failures to client-safe responses by failure category."""
    request.logger.error(
        "Database error",
        client_address=_client_address(request),
        error=str(exc),
    )
    if isinstance(exc, IntegrityError):
        return _error_response("Unable to store record", HTTP_409_CONFLICT)
    if isinstance(exc, OperationalError):
        return _error_response("Database unavailable", HTTP_503_SERVICE_UNAVAILABLE)
    return _error_response("Internal server error", HTTP_500_INTERNAL_SERVER_ERROR)
