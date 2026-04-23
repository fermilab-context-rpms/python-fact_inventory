"""Endpoint for root path.

Provides a trivial HTTP 200 response at the root path with minimal content.

Public API
----------
* root_handler - Root path endpoint handler

Endpoint
--------
``GET /`` - Returns HTTP 200 with empty JSON object.

Examples
--------
>>> response = client.get("/")
>>> response.status_code
200
"""

from litestar import Response, get
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example
from litestar.status_codes import HTTP_200_OK


@get(
    "/",
    status_code=HTTP_200_OK,
    tags=["root"],
    summary="Root endpoint",
    description="Returns HTTP 200 at the root path with minimal content.",
    include_in_schema=True,
    responses={
        HTTP_200_OK: ResponseSpec(
            data_container=dict,
            description="Root path successful",
            examples=[
                Example(
                    summary="Success",
                    description="Root path returns successfully.",
                    value={},
                )
            ],
        ),
    },
)
async def root_handler() -> Response[dict[str, object]]:
    """Return HTTP 200 at root path with empty JSON object.

    Returns
    -------
    Response[dict[str, object]]
        HTTP 200 with empty JSON object.
    """
    return Response(content={}, status_code=HTTP_200_OK)
