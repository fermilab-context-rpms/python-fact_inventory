"""Database configuration for the fact_inventory server.

Provides SQLAlchemyAsyncConfig setup and engine configuration.
"""

from urllib.parse import urlparse

from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
)
from advanced_alchemy.extensions.litestar.plugins.init.config.engine import EngineConfig

__all__ = ["create_sqlalchemy_config"]


from collections.abc import Mapping


def create_sqlalchemy_config(
    database_uri: str,
    *,  # keyword-only
    debug: bool,
    pool_settings: Mapping[str, int],
) -> SQLAlchemyAsyncConfig:
    """Create SQLAlchemyAsyncConfig with engine settings.

    Parameters
    ----------
    database_uri : str
        Database connection string.
    debug : bool
        Enable SQL echo for debugging.
    pool_settings : dict
        Pool configuration with keys: pool_size, pool_recycle, max_overflow,
        pool_timeout.

    Returns
    -------
    SQLAlchemyAsyncConfig
        Configured SQLAlchemy plugin configuration.
    """
    parsed = urlparse(database_uri)

    engine_config = EngineConfig(echo=debug)
    if parsed.scheme and "sqlite" not in str(parsed.scheme):
        engine_config = EngineConfig(  # pragma: no cover
            pool_size=pool_settings["pool_size"],
            pool_recycle=pool_settings["pool_recycle"],
            max_overflow=pool_settings["max_overflow"],
            pool_timeout=pool_settings["pool_timeout"],
            pool_pre_ping=True,
            echo=debug,
        )

    return SQLAlchemyAsyncConfig(
        engine_config=engine_config,
        connection_string=database_uri,
        session_config=AsyncSessionConfig(expire_on_commit=False),
        create_all=False,
    )
