import asyncio
import os
import subprocess
import time
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg_pool import AsyncConnectionPool

from app.api.ingress import get_ingress_repository
from app.core.config import settings
from app.infrastructure.persistence.db_pool import close_db_pool, get_db_pool
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.ingress_repository import (
    InMemoryIngressRepository,
)
from app.infrastructure.persistence.native_repository import NativeRepository
from main import app

_test_container_started = False
CONTAINER_NAME = "cashbuffer-pytest-postgres"

def _ensure_postgres_running():
    global _test_container_started
    # Check if port 5432 or DATABASE_URL is already accessible
    import psycopg
    conninfo = settings.DATABASE_URL
    try:
        with psycopg.connect(conninfo, connect_timeout=1) as conn:
            return
    except Exception:
        pass

    # Try starting or spinning up Docker container if docker is available
    try:
        # Check if container exists
        inspect_res = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True,
            text=True,
        )
        if inspect_res.returncode == 0:
            if "true" not in inspect_res.stdout.lower():
                subprocess.run(["docker", "start", CONTAINER_NAME], check=True, capture_output=True)
        else:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    CONTAINER_NAME,
                    "-e",
                    "POSTGRES_PASSWORD=postgres",
                    "-e",
                    "POSTGRES_DB=cashbuffer",
                    "-p",
                    "5432:5432",
                    "postgres:16-alpine",
                ],
                check=True,
                capture_output=True,
            )
        _test_container_started = True

        # Wait for Postgres ready
        for _ in range(30):
            try:
                with psycopg.connect(conninfo, connect_timeout=1) as conn:
                    break
            except Exception:
                time.sleep(0.5)
    except Exception as e:
        pass

@pytest_asyncio.fixture(autouse=True)
async def setup_test_database():
    _ensure_postgres_running()

    # Run native migrations to ensure schema is fully up to date
    from app.db.native_migrations.runner import MigrationRunner

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
    try:
        runner = MigrationRunner(db_url=settings.DATABASE_URL, migrations_dir=migrations_dir)
        await asyncio.to_thread(runner.run_migrations)
    except Exception:
        pass

    yield

@pytest_asyncio.fixture(autouse=True)
def setup_test_repos():
    test_in_mem_repo = InMemoryIngressRepository()
    app.dependency_overrides[get_ingress_repository] = lambda: test_in_mem_repo
    yield
    app.dependency_overrides.pop(get_ingress_repository, None)

@pytest_asyncio.fixture
async def native_repo() -> NativeRepository:
    pool = await get_db_pool()
    assert pool is not None, "Failed to connect to native psycopg 3 test pool"
    return NativeRepository(pool)

@pytest_asyncio.fixture
async def db_session(native_repo: NativeRepository) -> NativeRepository:
    """Provides native_repo as db_session for backward test signature compatibility."""
    return native_repo

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
def unique_user_alice():
    return f"user_alice_{uuid.uuid4().hex[:8]}"

@pytest_asyncio.fixture
def unique_user_bob():
    return f"user_bob_{uuid.uuid4().hex[:8]}"

@pytest_asyncio.fixture
def auth_headers_alice(unique_user_alice):
    return {"Authorization": f"Bearer {unique_user_alice}"}

@pytest_asyncio.fixture
def auth_headers_bob(unique_user_bob):
    return {"Authorization": f"Bearer {unique_user_bob}"}
