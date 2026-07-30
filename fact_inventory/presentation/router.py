"""Top-level router for the fact_inventory application.

Health and readiness probes are mounted at the top level (not under /api).
All API endpoints (versioned endpoints) are mounted under /api.

Parameters
----------
path : str, optional
    Mount point for the router. Use "/" for standalone deployment
    (the default) or a prefix such as "/fact_inventory" when
    embedding in a larger application.

Returns
-------
Router
    Fully assembled router ready to pass to Litestar.

Examples
--------
>>> router = create_router()


Parameters
----------
path : str, optional
    Mount point for the router. Use "/" for standalone deployment
    (the default) or a prefix such as "/fact_inventory" when
    embedding in a larger application.

Returns
-------
Router
    Fully assembled router ready to pass to Litestar.

Examples
--------
>>> router = create_router()
>>> app = Litestar(route_handlers=[router])
>>> router = create_router(path="/fact_inventory")
>>> app = Litestar(route_handlers=[router])
"""

from typing import Any

from litestar import Router

from fact_inventory.lib.settings import settings
from fact_inventory.presentation.api.router import create_router as create_api_router
from fact_inventory.presentation.health import health_check
from fact_inventory.presentation.ready import ready_check
from fact_inventory.presentation.root import root_handler

__all__ = ["create_router"]


def create_router(path: str = "/") -> Router:
    """Return a Router with all handlers mounted.

    Parameters
    ----------
    path : str, optional
        Mount point for the router. Use "/fact_inventory" for standalone deployment
        (the default) or a prefix such as "/fact_inventory" when
        embedding in a larger application.

    Returns
    -------
    Router
        Fully assembled router ready to pass to Litestar.
    """
    route_handlers: list[Any] = [root_handler, create_api_router()]

    if settings.enable_health_endpoint:
        route_handlers.append(health_check)

    if settings.enable_ready_endpoint:
        route_handlers.append(ready_check)

    return Router(
        path=path,
        route_handlers=route_handlers,
    )
