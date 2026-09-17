import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import AsyncSessionLocal, Base, engine
from main import app


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


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
