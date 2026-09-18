import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quarantine_queue(client: AsyncClient, auth_headers_alice: dict, unique_user_alice: str):
    # 1. Post valid email webhook
    valid_email = "INR 450.00 has been debited from your A/c no. XX1234 on 15-09-2026. Info: UPI/SWIGGY/ORDER_9876."
    res = await client.post(
        "/api/v1/ingestion/email-webhook",
        headers=auth_headers_alice,
        json={"email_text": valid_email},
    )
    assert res.status_code == 200

    # 2. Post invalid emails that get quarantined
    invalid_email_1 = "This is definitely NOT a valid banking alert. Ignore it."
    res_err1 = await client.post(
        "/api/v1/ingestion/email-webhook",
        headers=auth_headers_alice,
        json={"email_text": invalid_email_1},
    )
    assert res_err1.status_code == 422

    invalid_email_2 = "INR alert somehow but missing standard structures here."
    res_err2 = await client.post(
        "/api/v1/ingestion/email-webhook",
        headers=auth_headers_alice,
        json={"email_text": invalid_email_2},
    )
    assert res_err2.status_code == 422

    # 3. Fetch quarantine queue
    q_res = await client.get("/api/v1/ingestion/quarantine", headers=auth_headers_alice)
    assert q_res.status_code == 200
    q_items = q_res.json()

    assert len(q_items) == 2
    assert q_items[0]["email_text"] == invalid_email_2
    assert q_items[1]["email_text"] == invalid_email_1
    assert q_items[0]["resolved"] is False

    # 4. Filter by resolved (should be empty for now)
    q_res_true = await client.get("/api/v1/ingestion/quarantine?resolved=true", headers=auth_headers_alice)
    assert q_res_true.status_code == 200
    assert len(q_res_true.json()) == 0
