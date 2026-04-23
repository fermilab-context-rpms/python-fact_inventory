"""Handlers for SQLAlchemy and advanced-alchemy errors."""

from typing import Any

from advanced_alchemy.exceptions import IntegrityError, NotFoundError, RepositoryError
from litestar import Response
from litestar.status_codes import (
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from fact_inventory.presentation.api.v1.exception_handlers.helpers import (
    _client_address,
    _error_response,
)

__all__ = ["repository_error_handler"]


def repository_error_handler(
    request: Any,
    exc: RepositoryError,
) -> Response[dict[str, Any]]:
    """Map advanced-alchemy repository failures to client-safe responses.

    Services built on ``SQLAlchemyAsyncRepositoryService`` wrap raw SQLAlchemy
    errors into advanced-alchemy's ``RepositoryError`` hierarchy, so database
    failures surface here rather than in :func:`sqlalchemy_error_handler`.
    """
    request.logger.error(
        "Database error",
        client_address=_client_address(request),
        error=str(exc),
    )
    if isinstance(exc, NotFoundError):
        return _error_response("Record not found", HTTP_404_NOT_FOUND)
    if isinstance(exc, IntegrityError):
        return _error_response("Unable to store record", HTTP_409_CONFLICT)
    return _error_response("Internal server error", HTTP_500_INTERNAL_SERVER_ERROR)
