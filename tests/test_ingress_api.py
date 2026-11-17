import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingress_endpoints_unauthorized(client: AsyncClient):
    # Missing auth bearer
    r1 = await client.get("/api/v1/ingress/config")
    assert r1.status_code == 401

    r2 = await client.patch("/api/v1/ingress/config", json={"interval_minutes": 30})
    assert r2.status_code == 401

    r3 = await client.post("/api/v1/ingress/trigger")
    assert r3.status_code == 401

    r4 = await client.get("/api/v1/ingress/status")
    assert r4.status_code == 401

@pytest.mark.asyncio
async def test_ingress_config_lifecycle(
    client: AsyncClient, auth_headers_alice: dict, unique_user_alice: str
):
    # 1. GET default config
    res = await client.get("/api/v1/ingress/config", headers=auth_headers_alice)
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "gmail"
    assert data["is_enabled"] is True
    assert data["interval_minutes"] == 60
    assert data["status"] == "idle"
    # Ensure internal user UUID mapping, not raw IDP subject
    assert data["user_id"] != unique_user_alice
    assert uuid.UUID(data["user_id"])
    assert uuid.UUID(data["household_id"])

    # 2. PATCH config with valid interval
    patch_res = await client.patch(
        "/api/v1/ingress/config",
        headers=auth_headers_alice,
        json={"interval_minutes": 30, "is_enabled": False},
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["interval_minutes"] == 30
    assert patch_data["is_enabled"] is False

    # 3. GET config confirms persisted change
    get_res = await client.get("/api/v1/ingress/config", headers=auth_headers_alice)
    assert get_res.status_code == 200
    assert get_res.json()["interval_minutes"] == 30
    assert get_res.json()["is_enabled"] is False

@pytest.mark.asyncio
async def test_ingress_interval_validation(client: AsyncClient, auth_headers_alice: dict):
    # Allowed intervals are (15, 30, 60, 360, 1440)
    invalid_intervals = [0, 5, 45, 100, 2000, -15]
    for inv in invalid_intervals:
        res = await client.patch(
            "/api/v1/ingress/config",
            headers=auth_headers_alice,
            json={"interval_minutes": inv},
        )
        assert res.status_code == 422, f"Expected 422 for interval {inv}"

    # Valid intervals pass
    for valid in [15, 30, 60, 360, 1440]:
        res = await client.patch(
            "/api/v1/ingress/config",
            headers=auth_headers_alice,
            json={"interval_minutes": valid},
        )
        assert res.status_code == 200
        assert res.json()["interval_minutes"] == valid

@pytest.mark.asyncio
async def test_ingress_atomic_trigger(client: AsyncClient, auth_headers_alice: dict):
    # Trigger immediate sync
    trigger_res = await client.post("/api/v1/ingress/trigger", headers=auth_headers_alice)
    assert trigger_res.status_code == 200
    data = trigger_res.json()
    assert data["message"] == "Sync triggered successfully"
    assert "next_run_at" in data
    assert data["config"]["provider"] == "gmail"

@pytest.mark.asyncio
async def test_ingress_status(client: AsyncClient, auth_headers_alice: dict):
    status_res = await client.get("/api/v1/ingress/status", headers=auth_headers_alice)
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["provider"] == "gmail"
    assert data["status"] in ["idle", "running", "failed"]
    assert "total_processed" in data
    assert "household_id" in data
    assert uuid.UUID(data["household_id"])

@pytest.mark.asyncio
async def test_ingress_tenant_isolation(
    client: AsyncClient,
    auth_headers_alice: dict,
    auth_headers_bob: dict,
    unique_user_alice: str,
    unique_user_bob: str,
):
    # Set Alice config to 15 minutes, enabled=False
    alice_patch = await client.patch(
        "/api/v1/ingress/config",
        headers=auth_headers_alice,
        json={"interval_minutes": 15, "is_enabled": False},
    )
    assert alice_patch.status_code == 200
    alice_data = alice_patch.json()

    # Bob fetches config - must receive Bob's separate household defaults (60m, True)
    bob_res = await client.get("/api/v1/ingress/config", headers=auth_headers_bob)
    assert bob_res.status_code == 200
    bob_data = bob_res.json()

    assert alice_data["household_id"] != bob_data["household_id"]
    assert alice_data["user_id"] != bob_data["user_id"]
    assert bob_data["interval_minutes"] == 60
    assert bob_data["is_enabled"] is True

    # Mutate Bob's config to 360m
    await client.patch(
        "/api/v1/ingress/config",
        headers=auth_headers_bob,
        json={"interval_minutes": 360, "is_enabled": True},
    )

    # Verify Alice's config unchanged
    alice_check = await client.get("/api/v1/ingress/config", headers=auth_headers_alice)
    assert alice_check.status_code == 200
    assert alice_check.json()["interval_minutes"] == 15
    assert alice_check.json()["is_enabled"] is False
