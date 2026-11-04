import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_telegram_link_and_unlink(client: AsyncClient, auth_headers_alice, unique_user_alice):
    me = await client.get("/api/v1/auth/me", headers=auth_headers_alice)
    assert me.status_code == 200

    link_res = await client.post("/api/v1/auth/link-telegram?telegram_chat_id=1234567890", headers=auth_headers_alice)
    assert link_res.status_code == 200

    me_linked = await client.get("/api/v1/auth/me", headers=auth_headers_alice)
    assert me_linked.json()["telegram_chat_id"] == "1234567890"

    unlink_res = await client.post("/api/v1/telegram/unlink", headers=auth_headers_alice)
    assert unlink_res.status_code == 200

    me_unlinked = await client.get("/api/v1/auth/me", headers=auth_headers_alice)
    assert me_unlinked.json()["telegram_chat_id"] is None
