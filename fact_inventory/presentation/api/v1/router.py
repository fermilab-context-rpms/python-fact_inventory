"""Router for the v1 API.

Assembles the /v1 namespace with all fact submission handlers.

Parameters
----------
v1_router : Router
    The Router instance mounted at ``/v1``.

Examples
--------
To submit system and package facts, send a POST request to /api/v1/facts.
"""

from advanced_alchemy.extensions.litestar.providers import create_service_provider
from litestar import Router
from litestar.di import Provide

from fact_inventory.application.services import FactInventoryService
from fact_inventory.presentation.api.v1.controller import FactInventoryController

__all__ = ["v1_router"]

v1_router: Router = Router(
    path="/v1",
    route_handlers=[FactInventoryController],
    tags=["api", "v1"],
    dependencies={
        "fact_inventory_service": Provide(
            create_service_provider(FactInventoryService)
        ),
    },
)
