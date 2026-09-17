import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_idempotency_direct_ingestion():
    """Duplicate direct ingests should return the same transaction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "amount": 1500.0,
            "currency": "INR",
            "is_inflow": False,
            "record_date": "2024-03-10",
            "vendor_raw": "Starbucks Coffee",
            "auto_categorize": False,
        }
        headers = {"Authorization": "Bearer TEST_TOKEN_USER_1"}

        r1 = await client.post("/api/v1/ingestion/direct", json=payload, headers=headers)
        assert r1.status_code == 200
        tx1 = r1.json()

        r2 = await client.post("/api/v1/ingestion/direct", json=payload, headers=headers)
        assert r2.status_code == 200
        tx2 = r2.json()

        assert tx1["id"] == tx2["id"]


@pytest.mark.asyncio
async def test_idempotency_batch_ingestion():
    """Duplicate items within a batch should be deduplicated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "transactions": [
                {
                    "amount": 100.0,
                    "currency": "INR",
                    "is_inflow": False,
                    "record_date": "2024-03-11",
                    "vendor_raw": "Amazon",
                },
                {
                    "amount": 100.0,
                    "currency": "INR",
                    "is_inflow": False,
                    "record_date": "2024-03-11",
                    "vendor_raw": "Amazon",
                },
            ],
            "auto_categorize": False,
        }
        headers = {"Authorization": "Bearer TEST_TOKEN_USER_1"}

        r = await client.post("/api/v1/ingestion/batch", json=payload, headers=headers)
        assert r.status_code == 200
        res = r.json()

        # Both items resolve to same tx
        assert res[0]["id"] == res[1]["id"]
