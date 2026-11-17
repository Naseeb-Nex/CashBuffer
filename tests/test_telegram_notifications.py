import uuid

import pytest

from app.domain.models import TransactionStatus, User
from app.services.notifications import dispatch_all_catchups, process_telegram_update
from app.services.transactions import create_transaction, get_transaction_by_id

async def _link_user(db_session, user_id: str, chat_id: str) -> User:
    """Link telegram_chat_id the same way the authenticated /link-telegram API does."""
    user = await db_session.get_or_create_user(user_id)
    await db_session.set_telegram_chat_id(user.id, str(chat_id))
    return await db_session.get_user_by_id(user.id)

@pytest.mark.asyncio
async def test_telegram_start_does_not_link_account(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"555000{uuid.uuid4().int % 10000}"

    res = await process_telegram_update(
        db_session,
        {"message": {"chat": {"id": int(chat_id)}, "text": f"/start {user_id}"}},
    )
    assert res["status"] == "prompted_link"
    assert "user_id" not in res

    linked = await db_session.get_user_by_telegram_chat_id(str(chat_id))
    assert linked is None

    created = await db_session.get_user_by_idp(user_id)
    assert created is None

@pytest.mark.asyncio
async def test_telegram_start_prompt_and_summary(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"9876543{uuid.uuid4().int % 10000}"

    res = await process_telegram_update(
        db_session,
        {"message": {"chat": {"id": int(chat_id)}, "text": "/start"}},
    )
    assert res["status"] == "prompted_link"

    summary_update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": "/summary",
        }
    }
    sum_res_unlinked = await process_telegram_update(db_session, summary_update)
    assert sum_res_unlinked["status"] == "unlinked_chat"

    await _link_user(db_session, user_id, chat_id)

    # Ingest data
    await create_transaction(
        db_session,
        user_id=user_id,
        amount=5000.0,
        currency="INR",
        is_inflow=True,
        vendor_raw="Salary Deposit",
    )
    await create_transaction(
        db_session,
        user_id=user_id,
        amount=1200.0,
        currency="INR",
        is_inflow=False,
        vendor_raw="Grocery Store",
    )

    sum_res_linked = await process_telegram_update(db_session, summary_update)
    assert sum_res_linked["status"] == "summary_sent"

@pytest.mark.asyncio
async def test_telegram_catchup_dispatch_and_categorize(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"1234567{uuid.uuid4().int % 10000}"

    user = await _link_user(db_session, user_id, chat_id)

    # Create transaction needing review
    tx = await create_transaction(
        db_session,
        user_id=user_id,
        amount=450.0,
        vendor_raw="Zomato Order 123",
        auto_categorize=True,
    )
    assert tx.status == TransactionStatus.NEEDS_REVIEW

    # Dispatch catch-up
    res = await dispatch_all_catchups(db_session, user_id=user_id)
    assert res["dispatched"] == 1
    assert res["results"][0]["pending_count"] >= 1

    # User responds via Telegram: /cat <tx_id> Food & Dining
    cat_update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": f"/cat {tx.id} Food & Dining",
        }
    }
    cat_res = await process_telegram_update(db_session, cat_update)
    assert cat_res["status"] == "categorized"
    assert cat_res["tx_id"] == tx.id

    # Verify transaction is now categorized
    refreshed = await get_transaction_by_id(db_session, user_id, tx.id)
    assert refreshed.status == TransactionStatus.CATEGORIZED
