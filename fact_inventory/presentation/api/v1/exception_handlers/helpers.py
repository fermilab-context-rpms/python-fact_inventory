"""Helper functions for exception handlers."""

from typing import Any

from litestar import Response

from fact_inventory.presentation.api.v1.schemas.responses import APIResponse

__all__ = ["_client_address", "_error_response"]


def _client_address(request: Any) -> str:
    """Return the client IP address from the request, or 'unknown'."""
    return request.client.host if request.client is not None else "unknown"


def _error_response(
    detail: str,
    status_code: int,
) -> Response[dict[str, Any]]:
    """Build a JSON error response using the API envelope."""
    return Response(
        media_type="application/json",
        status_code=status_code,
        content=APIResponse(
            status="error",
            detail=detail,
            data=None,
        ).model_dump(),
    )
