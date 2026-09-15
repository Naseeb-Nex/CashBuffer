import uuid

import pytest

from app.db.models import TransactionStatus
from app.services.notifications import dispatch_all_catchups, process_telegram_update
from app.services.transactions import create_transaction, get_transaction_by_id


@pytest.mark.asyncio
async def test_telegram_link_and_summary(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"9876543{uuid.uuid4().int % 10000}"

    # 1. User sends /start <user_id>
    update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": f"/start {user_id}",
        }
    }
    res = await process_telegram_update(db_session, update)
    assert res["status"] == "linked"
    assert res["user_id"] == user_id

    # 2. Add some transactions
    await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=5000.0,
        is_inflow=True,
        vendor_raw="Client Payment",
    )
    await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=1200.0,
        is_inflow=False,
        vendor_raw="Fancy Cafe",
    )

    # 3. User asks /summary
    summary_update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": "/summary",
        }
    }
    sum_res = await process_telegram_update(db_session, summary_update)
    assert sum_res["status"] == "summary_sent"


@pytest.mark.asyncio
async def test_telegram_catchup_dispatch_and_categorize(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"112233{uuid.uuid4().int % 10000}"

    # Link user
    link_update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": f"/start {user_id}",
        }
    }
    await process_telegram_update(db_session, link_update)

    # Ingest uncategorized transaction
    tx = await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=890.0,
        vendor_raw="NETFLIX SUBSCRIPTION",
        auto_categorize=True,
    )
    assert tx.status == TransactionStatus.NEEDS_REVIEW

    # Dispatch catchup
    catchup_res = await dispatch_all_catchups(db_session, user_id=user_id)
    assert len(catchup_res["results"]) >= 1
    assert catchup_res["results"][0]["user_id"] == user_id

    # User replies with /cat <tx_id> Entertainment
    cat_update = {
        "message": {
            "chat": {"id": int(chat_id)},
            "text": f"/cat {tx.id} Entertainment",
        }
    }
    cat_res = await process_telegram_update(db_session, cat_update)
    assert cat_res["status"] == "categorized"
    assert cat_res["category"] == "Entertainment"

    # Verify transaction is now CATEGORIZED
    updated_tx = await get_transaction_by_id(db_session, user_id, tx.id)
    assert updated_tx.status == TransactionStatus.CATEGORIZED
