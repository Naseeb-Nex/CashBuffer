import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation_transactions(client: AsyncClient, auth_headers_alice, auth_headers_bob):
    # Alice creates a transaction
    res_alice = await client.post(
        "/api/v1/ingestion/direct",
        headers=auth_headers_alice,
        json={
            "amount": 1500.0,
            "currency": "INR",
            "is_inflow": False,
            "vendor_raw": "Alice Secret Shop",
        },
    )
    assert res_alice.status_code == 200
    alice_tx_id = res_alice.json()["id"]

    # Bob tries to access Alice's transaction directly
    res_bob_view = await client.get(
        f"/api/v1/transactions/{alice_tx_id}",
        headers=auth_headers_bob,
    )
    assert res_bob_view.status_code == 404

    # Bob lists his transactions -> must not see Alice's transaction
    res_bob_list = await client.get(
        "/api/v1/transactions",
        headers=auth_headers_bob,
    )
    assert res_bob_list.status_code == 200
    bob_tx_ids = [tx["id"] for tx in res_bob_list.json()]
    assert alice_tx_id not in bob_tx_ids

    # Bob tries to delete Alice's transaction -> must fail
    res_bob_del = await client.delete(
        f"/api/v1/transactions/{alice_tx_id}",
        headers=auth_headers_bob,
    )
    assert res_bob_del.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_llm_config(client: AsyncClient, auth_headers_alice, auth_headers_bob):
    # Alice sets LLM config
    await client.post(
        "/api/v1/llm-config",
        headers=auth_headers_alice,
        json={
            "provider": "anthropic",
            "model_name": "claude-3-5-sonnet",
            "api_key": "sk-ant-alice-secret-key-12345",
        },
    )

    # Bob checks LLM config -> should be None
    res_bob_cfg = await client.get(
        "/api/v1/llm-config",
        headers=auth_headers_bob,
    )
    assert res_bob_cfg.status_code == 200
    assert res_bob_cfg.json() is None
