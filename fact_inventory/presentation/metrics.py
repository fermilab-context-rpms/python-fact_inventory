"""Prometheus metrics endpoint.

Provides a Prometheus-compatible metrics endpoint at /fact_inventory/metrics.
"""

from litestar.plugins.prometheus import PrometheusController

from fact_inventory.lib.settings import settings


class FactInventoryPrometheusController(PrometheusController):
    """Prometheus metrics controller mounted at {app_prefix}/metrics."""

    path: str = f"{settings.app_prefix}/metrics"
