"""Test database setup and migration helpers."""

import os
import subprocess
import sys
from pathlib import Path

__all__ = [
    "TestDatabaseSetup",
    "run_migrations",
]


class TestDatabaseSetup:
    """Configure and manage test database for pytest."""

    # Environment variable for auto-generated database URIs
    _AUTO_DATABASE_URI_ENV = "FACT_INVENTORY_TEST_AUTO_DATABASE_URI"

    def __init__(self) -> None:
        """Initialize test database configuration."""
        self.worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
        self.project_root = Path(__file__).parent.parent.parent
        self.cache_dir = self.project_root / ".pytest_cache"
        self.db_file = self.cache_dir / f"test_migrations.{self.worker_id}.db"
        self.managed_db_file: Path | None = None

    def setup(self) -> None:
        """Set up environment variables for test database."""
        self._ensure_cache_dir()
        self._configure_database_uri()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory for test database."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _configure_database_uri(self) -> None:
        """Configure DATABASE_URI environment variable.

        Respects explicit overrides from CI/CD or manual runs while providing
        sensible defaults for xdist workers.
        """
        default_uri = f"sqlite+aiosqlite:///{self.db_file}"

        if (
            "DATABASE_URI" not in os.environ
            or os.environ.get(self._AUTO_DATABASE_URI_ENV) == "1"
        ):
            os.environ["DATABASE_URI"] = default_uri
            os.environ[self._AUTO_DATABASE_URI_ENV] = "1"
            self.managed_db_file = self.db_file
        else:
            # User provided explicit DATABASE_URI; don't manage cleanup
            self.managed_db_file = None

    def cleanup_db_file(self) -> None:
        """Remove test database file if we created it."""
        if self.managed_db_file is not None:
            self.managed_db_file.unlink(missing_ok=True)


def run_migrations(project_root: Path | None = None) -> None:
    """Run Alembic migrations for the test database.

    Ensures tests use the same migration path as production code, verifying
    that migrations actually work.

    Args:
        project_root: Root directory of the project (defaults to parent of tests/)

    Raises:
        RuntimeError: If migrations fail.
    """
    # Import here to ensure DEPLOYMENT is already set by conftest
    from fact_inventory.lib.settings import settings as app_settings

    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    env = os.environ.copy()
    env["DATABASE_URI"] = app_settings.database_uri

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:  # pragma: no cover
        msg = (
            f"Alembic migrations failed:\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        raise RuntimeError(msg)
