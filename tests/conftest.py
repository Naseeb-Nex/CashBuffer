import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.ingress import get_ingress_repository
from app.infrastructure.persistence.ingress_repository import (
    InMemoryIngressRepository,
)
from main import app

@pytest_asyncio.fixture(autouse=True)
def setup_test_repos():
    test_in_mem_repo = InMemoryIngressRepository()
    app.dependency_overrides[get_ingress_repository] = lambda: test_in_mem_repo
    yield
    app.dependency_overrides.pop(get_ingress_repository, None)

@pytest_asyncio.fixture(autouse=True)
async def init_legacy_db_if_sqlite():
    from app.core.config import settings
    if "sqlite" in settings.DATABASE_URL:
        from app.db.database import Base, engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def db_session():
    from app.core.config import settings
    if "sqlite" in settings.DATABASE_URL:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            yield session
    else:
        yield None

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
