"""API router factory for fact_inventory.

Assembles all versioned API routes with rate limiting applied.

Examples
--------
>>> router = create_router()
>>> app = Litestar(route_handlers=[router])
"""

from litestar import Router
from litestar.middleware.rate_limit import RateLimitConfig

from fact_inventory.lib.settings import Settings, get_settings
from fact_inventory.presentation.api.api_is_mounted import api_is_mounted
from fact_inventory.presentation.api.v1.router import create_v1_router

__all__ = ["create_router"]


def create_router(settings: Settings | None = None) -> Router:
    """Return a Router with all API handlers and rate limiting applied.

    Parameters
    ----------
    settings : Settings | None
        Application configuration. Required to configure rate limiting.

    Returns
    -------
    Router
        Fully assembled API router ready to be mounted under /api.
    """
    if settings is None:
        settings = get_settings()

    rate_limit_config = RateLimitConfig(
        rate_limit=(settings.api_rate_limit_unit, settings.api_rate_limit_max_requests),
        set_rate_limit_headers=settings.api_rate_limit_headers,
    )

    return Router(
        path="/api",
        route_handlers=[api_is_mounted, create_v1_router(settings)],
        middleware=[rate_limit_config.middleware],
    )
