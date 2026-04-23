"""API router status endpoint.

Provides a health check for the API router itself, verifying that the API
layer is properly mounted and accessible at the root of the API path.

Public API
----------
* api_is_mounted - API root status endpoint handler

Endpoint
--------
``GET /api`` - Returns HTTP 200 when the API router is mounted.
"""

from litestar import Response, get
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example
from litestar.status_codes import HTTP_200_OK

from fact_inventory.lib.settings import settings


@get(
    status_code=HTTP_200_OK,
    tags=["api"],
    summary="API router mounted check",
    description=(
        "Returns HTTP 200 when the API router is mounted and accessible."
        " Use this endpoint to verify that the API layer is properly configured."
    ),
    include_in_schema=True,
    responses={
        HTTP_200_OK: ResponseSpec(
            data_container=None,
            description="API router is mounted",
            examples=[
                Example(
                    summary="API mounted",
                    description="The API router is properly mounted and accessible.",
                    value={"app": "fact_inventory"},
                )
            ],
        ),
    },
)
async def api_is_mounted() -> Response[dict[str, str]]:
    """Return 200OK when the API router is mounted.

    Returns
    -------
    Response[dict[str, str]]
        HTTP 200 with app name and status.
    """
    return Response(
        content={"app": settings.app_name},
        status_code=HTTP_200_OK,
    )
