"""Compatibility re-export of the ASGI application.

Warning
-------
Litestar is an ASGI framework. The object returned by ``create_app()`` is an
ASGI application, not a WSGI application. The ``app`` object below must be
served by an ASGI server (uvicorn, gunicorn with a uvicorn worker, hypercorn,
etc.) or wrapped with an ASGI-to-WSGI bridge before use with a WSGI server.

Note
----
This module requires configuration (DEPLOYMENT and DATABASE_URI environment
variables) to be set before import. For a lazy-loading variant that defers
configuration validation, use ``fact_inventory.server.app:create_app`` as a
factory function instead.
"""

from fact_inventory.server.app import create_app

app = create_app()

__all__ = ["app"]
