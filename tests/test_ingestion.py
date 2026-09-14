import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from datetime import date

from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

from app.api.auth import get_current_user
from app.db.database import AsyncSessionLocal, Base, engine
from app.db.models import User
from main import app


# Create a test setup
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def users(setup_db):
    u1_id, u2_id = "user1", "user2"
    async with AsyncSessionLocal() as session:
        # Check if they exist first, drop and recreate them to avoid UNIQUE constraint
        exist = await session.execute(select(User).where(User.id.in_([u1_id, u2_id])))
        exist_users = exist.scalars().all()
        if exist_users:
            for u in exist_users:
                await session.delete(u)
            await session.commit()

        u1 = User(id=u1_id, email="u1@example.com")
        u2 = User(id=u2_id, email="u2@example.com")
        session.add(u1)
        session.add(u2)
        await session.commit()
    yield {"user1": u1_id, "user2": u2_id}


@pytest.mark.asyncio
async def test_category_idor(client, users):
    app.dependency_overrides[get_current_user] = lambda: users["user1"]

    resp = await client.post("/ingest/categories", json=[{"name": "U1 Cat"}])
    assert resp.status_code == 200
    ids = resp.json().get("ids")
    u1_cat_id = ids[0]

    app.dependency_overrides[get_current_user] = lambda: users["user2"]
    resp2 = await client.post(
        "/ingest/categories", json=[{"name": "U2 Cat", "parent_id": u1_cat_id}]
    )
    assert resp2.status_code == 403


@pytest.mark.asyncio
async def test_user_telegram_chat_id_clear(client, users):
    app.dependency_overrides[get_current_user] = lambda: users["user1"]

    # Set telegram id
    resp1 = await client.post(
        "/ingest/user", json={"email": "u1@example.com", "telegram_chat_id": "12345"}
    )
    assert resp1.status_code == 200

    # Clear using empty string (which is now correctly handled vs None)
    resp2 = await client.post(
        "/ingest/user", json={"email": "u1@example.com", "telegram_chat_id": ""}
    )
    assert resp2.status_code == 200

    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.id == "user1"))).scalar_one()
        assert u.telegram_chat_id == ""


@pytest.mark.asyncio
async def test_user_email_conflict(client, users):
    app.dependency_overrides[get_current_user] = lambda: users["user1"]
    resp = await client.post("/ingest/user", json={"email": "u2@example.com"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transactions_returns_ids(client, users):
    app.dependency_overrides[get_current_user] = lambda: users["user1"]
    tx_data = {
        "amount": 10.5,
        "is_inflow": False,
        "record_date": str(date.today()),
        "vendor_raw": "Test Vendor",
    }

    resp = await client.post("/ingest/transactions", json=[tx_data])
    assert resp.status_code == 200
    assert "ids" in resp.json()
    assert len(resp.json()["ids"]) == 1
    assert resp.json()["ids"][0] is not None
