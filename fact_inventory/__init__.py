from fact_inventory.server.app import create_app as app_factory

__all__ = ["app", "app_factory", "application"]

app = app_factory()
application = app
