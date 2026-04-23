"""Prometheus metrics endpoint.

Provides a Prometheus-compatible metrics controller. The concrete mount path
is set by the application factory because it depends on the configured
``APP_PREFIX``; this module intentionally does not import settings so the
package remains importable before configuration is available.
"""

from litestar.plugins.prometheus import PrometheusController

__all__ = ["FactInventoryPrometheusController"]


class FactInventoryPrometheusController(PrometheusController):
    """Base Prometheus metrics controller.

    The final ``path`` is assigned dynamically by ``create_app`` so it can
    include the configured application prefix.
    """

    path: str = "/metrics"


def create_metrics_controller(path: str) -> type[FactInventoryPrometheusController]:
    """Return a Prometheus controller subclass mounted at ``path``.

    Parameters
    ----------
    path : str
        Mount point for the metrics endpoint, including any application prefix.

    Returns
    -------
    type[FactInventoryPrometheusController]
        Controller class with ``path`` set to the requested value.
    """
    return type(
        "PrefixedPrometheusController",
        (FactInventoryPrometheusController,),
        {"path": path},
    )
