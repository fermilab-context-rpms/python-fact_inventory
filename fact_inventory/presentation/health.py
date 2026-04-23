"""Endpoint for health checks.

Provides a fast liveness check with no external dependencies or database calls.
Suitable for Kubernetes liveness probes that need to respond quickly.

Public API
----------
* health_check - Fast liveness endpoint handler

Endpoint
--------
``GET /health`` - Returns HTTP 200 when the application process is running.
No external dependencies are called, making this suitable for rapid health
checks.

Examples
--------
>>> response = client.get("/health")
>>> response.status_code
200
"""

from litestar import Response, get
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example
from litestar.status_codes import HTTP_200_OK


@get(
    "/health",
    status_code=HTTP_200_OK,
    tags=["health"],
    summary="Application liveness check",
    description=(
        "Returns HTTP 200 when the application process is running and able to"
        " serve requests.  This endpoint has no external dependencies (no"
        " database call) so it can be used as a fast liveness probe."
    ),
    include_in_schema=True,
    responses={
        HTTP_200_OK: ResponseSpec(
            data_container=dict,
            description="Service is alive",
            examples=[
                Example(
                    summary="Healthy",
                    description="The application process is running normally.",
                    value={"status": "healthy"},
                )
            ],
        ),
    },
)
async def health_check() -> Response[dict[str, str]]:
    """Return liveness status indicating the application process is running.

    This endpoint provides a fast health check with no external dependencies
    or database calls, suitable for Kubernetes liveness probes.

    Returns
    -------
    Response[dict[str, str]]
        HTTP 200 with JSON status body.
    """
    return Response(content={"status": "healthy"}, status_code=HTTP_200_OK)
