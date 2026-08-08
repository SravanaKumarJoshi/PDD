"""Shared pytest fixtures for backend tests.

Provides:
  - Test database fixtures using testcontainers (if available)
  - FastAPI TestClient with overridden dependencies
  - Auth overrides (mock user / admin)

When no Postgres is available (no testcontainers, no DATABASE_URL),
integration tests that require a database are automatically skipped.
"""

import os
import pytest

os.environ["TESTING"] = "true"

# ── Determine test database URL ───────────────────────────────────
# Priority:
# 1. DATABASE_URL env var (CI with Postgres service container)
# 2. testcontainers (local dev with Docker)
# 3. None → integration tests auto-skip

TEST_DB_URL = os.getenv("DATABASE_URL")

_container = None

if not TEST_DB_URL:
    try:
        from testcontainers.postgres import PostgresContainer  # type: ignore
        _container = PostgresContainer("postgres:16-alpine")
        _container.start()
        sync_url = _container.get_connection_url()
        TEST_DB_URL = sync_url.replace("psycopg2", "asyncpg").replace("postgresql://", "postgresql+asyncpg://")
    except Exception:
        # testcontainers not available or Docker not running — that's fine
        TEST_DB_URL = None


def pytest_sessionfinish(session, exitstatus):
    """Clean up testcontainer on session end."""
    global _container
    if _container:
        try:
            _container.stop()
        except Exception:
            pass
        _container = None
