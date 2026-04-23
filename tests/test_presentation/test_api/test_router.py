"""Tests for the API router factory."""

from fact_inventory.presentation.api.router import create_router


def test_create_router_without_settings_resolves_settings() -> None:
    """Calling create_router() with no settings resolves them via get_settings()."""
    router = create_router()

    assert router.path == "/api"
    paths = {route.path for route in router.routes}
    assert "/api" in paths
    assert "/api/v1/facts" in paths
