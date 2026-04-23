"""Development entry point that creates the ASGI app and optionally runs uvicorn.

Run the development server with ``python -m fact_inventory`` or
``uvicorn fact_inventory:app``.

Environment variables
---------------------
HOST : str, optional
    Server host to bind to. Default is "localhost".
PORT : str, optional
    Server port to bind to. Default is "8000".
"""

import os

import uvicorn

host = os.getenv("HOST", "localhost")
port = int(os.getenv("PORT", "8000"))

uvicorn.run("fact_inventory:app", host=host, port=port, reload=True)
