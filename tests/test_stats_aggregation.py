import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats_summary_aggregation(client: AsyncClient, auth_headers_alice, unique_user_alice):
    # 1. Ingest transactions to simulate activity across "multiple accounts" dynamically handled
    batch_res = await client.post(
        "/api/v1/ingestion/batch",
        headers=auth_headers_alice,
        json={
            "transactions": [
                {"amount": 1000.0, "vendor_raw": "BankA Salary", "is_inflow": True},
                {"amount": 200.0, "vendor_raw": "BankB Grocery", "is_inflow": False},
                {"amount": 50.0, "vendor_raw": "BankC Coffee", "is_inflow": False}
            ]
        }
    )
    assert batch_res.status_code == 200

    # 2. Call stats integration endpoint
    res = await client.get("/api/v1/transactions/summary", headers=auth_headers_alice)
    assert res.status_code == 200
    data = res.json()

    assert data["total_inflow"] == 1000.0
    assert data["total_outflow"] == 250.0
    assert data["net_buffer"] == 750.0
    assert data["transaction_count"] >= 3
    assert "linked_accounts_count" in data
