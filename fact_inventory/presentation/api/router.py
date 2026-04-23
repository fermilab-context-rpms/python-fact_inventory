"""API router factory for fact_inventory.

Assembles all versioned API routes with rate limiting applied.

Examples
--------
>>> router = create_router()
>>> app = Litestar(route_handlers=[router])
"""

from litestar import Router
from litestar.middleware.rate_limit import RateLimitConfig

from fact_inventory.lib.settings import settings
from fact_inventory.presentation.api.api_is_mounted import api_is_mounted
from fact_inventory.presentation.api.v1.router import v1_router

__all__ = ["create_router"]


def create_router() -> Router:
    """Return a Router with all API handlers and rate limiting applied.

    Returns
    -------
    Router
        Fully assembled API router ready to be mounted under /api.
    """
    rate_limit_config = RateLimitConfig(
        rate_limit=(settings.api_rate_limit_unit, settings.api_rate_limit_max_requests),
        set_rate_limit_headers=settings.debug,
    )

    return Router(
        path="/api",
        route_handlers=[api_is_mounted, v1_router],
        middleware=[rate_limit_config.middleware],
    )
