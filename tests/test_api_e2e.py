import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_e2e_full_lifecycle(client: AsyncClient, auth_headers_alice, unique_user_alice):
    # 1. Check health
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    # 2. Check Auth Profile
    me = await client.get("/api/v1/auth/me", headers=auth_headers_alice)
    assert me.status_code == 200
    assert me.json()["id"] == unique_user_alice

    # 3. List categories (auto-seeded)
    cats_res = await client.get("/api/v1/categories", headers=auth_headers_alice)
    assert cats_res.status_code == 200
    categories = cats_res.json()
    assert len(categories) >= 5
    food_cat = next((c for c in categories if "Food" in c["name"]), categories[0])

    # 4. Direct Ingest Transaction
    tx_res = await client.post(
        "/api/v1/ingestion/direct",
        headers=auth_headers_alice,
        json={
            "amount": 420.0,
            "currency": "INR",
            "is_inflow": False,
            "vendor_raw": "UPI/ZOMATO_EATS_5544",
        },
    )
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    assert tx_data["amount"] == 420.0
    assert tx_data["status"] == "needs_review"
    tx_id = tx_data["id"]

    # 5. Ingest Batch
    batch_res = await client.post(
        "/api/v1/ingestion/batch",
        headers=auth_headers_alice,
        json={
            "transactions": [
                {
                    "amount": 35000.0,
                    "currency": "INR",
                    "is_inflow": True,
                    "vendor_raw": "Monthly Salary Transfer",
                },
                {
                    "amount": 2500.0,
                    "currency": "INR",
                    "is_inflow": False,
                    "vendor_raw": "Electricity Board Bill",
                },
            ]
        },
    )
    assert batch_res.status_code == 200
    assert len(batch_res.json()) == 2

    # 6. Ingest Raw Bank Email Webhook
    email_res = await client.post(
        "/api/v1/ingestion/email-webhook",
        headers=auth_headers_alice,
        json={"email_text": "INR 650.00 has been debited on 15-09-2026 Info: UPI/ZOMATO_DELIVERY."},
    )
    assert email_res.status_code == 200
    assert email_res.json()["amount"] == 650.0

    # 7. Create Vendor Rule for Zomato -> Food & Dining
    rule_res = await client.post(
        "/api/v1/rules",
        headers=auth_headers_alice,
        json={
            "vendor_regex": "zomato",
            "default_category_id": food_cat["id"],
            "re_evaluate_pending": True,
        },
    )
    assert rule_res.status_code == 200
    assert rule_res.json()["vendor_regex"] == "zomato"

    # 8. Check that original transaction is now auto-categorized!
    check_tx = await client.get(
        f"/api/v1/transactions/{tx_id}",
        headers=auth_headers_alice,
    )
    assert check_tx.status_code == 200
    assert check_tx.json()["status"] == "categorized"
    assert check_tx.json()["category_id"] == food_cat["id"]

    # 9. Ingest new Zomato transaction -> auto-categorized on creation
    new_zomato = await client.post(
        "/api/v1/ingestion/direct",
        headers=auth_headers_alice,
        json={
            "amount": 890.0,
            "currency": "INR",
            "is_inflow": False,
            "vendor_raw": "ZOMATO RESTAURANT",
        },
    )
    assert new_zomato.status_code == 200
    assert new_zomato.json()["status"] == "categorized"
    assert new_zomato.json()["category_id"] == food_cat["id"]

    # 9.5 Test Advanced Filering
    list_res = await client.get(
        "/api/v1/transactions",
        headers=auth_headers_alice,
        params={"min_amount": 1000, "max_amount": 3000, "search": "Electricity"}
    )
    assert list_res.status_code == 200
    filtered = list_res.json()
    assert len(filtered) == 1
    assert filtered[0]["amount"] == 2500.0

    list_res_2 = await client.get(
        "/api/v1/transactions",
        headers=auth_headers_alice,
        params={"min_amount": 50000}
    )
    assert list_res_2.json() == []

    # 10. Financial Summary API
    summary_res = await client.get(
        "/api/v1/transactions/summary",
        headers=auth_headers_alice,
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_inflow"] == 35000.0
    assert summary["net_buffer"] > 0
    assert len(summary["category_breakdown"]) > 0

    # 11. Assistant Chat API
    chat_res = await client.post(
        "/api/v1/assistant/chat",
        headers=auth_headers_alice,
        json={"message": "What is my spending overview and net buffer?"},
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "reply" in chat_data
    assert len(chat_data["reply"]) > 0
