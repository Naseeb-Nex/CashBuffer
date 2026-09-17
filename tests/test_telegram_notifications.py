import uuid

import pytest
from sqlalchemy import select

from app.db.models import TransactionStatus, User
from app.services.notifications import dispatch_all_catchups, process_telegram_update
from app.services.transactions import create_transaction, get_transaction_by_id


async def _link_user(db_session, user_id: str, chat_id: str) -> User:
    """Link telegram_chat_id the same way the authenticated /link-telegram API does."""
    user = User(id=user_id, email=f"{user_id}@cashbuffer.local", telegram_chat_id=str(chat_id))
    db_session.add(user)
    await db_session.commit()
    return user


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

    stmt = select(User).where(User.telegram_chat_id == str(chat_id))
    linked = (await db_session.execute(stmt)).scalar_one_or_none()
    assert linked is None

    stmt = select(User).where(User.id == user_id)
    created = (await db_session.execute(stmt)).scalar_one_or_none()
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

    sum_res = await process_telegram_update(db_session, summary_update)
    assert sum_res["status"] == "summary_sent"
    assert sum_res["user_id"] == user_id


@pytest.mark.asyncio
async def test_telegram_catchup_dispatch_and_categorize(db_session):
    user_id = f"test_tg_user_{uuid.uuid4().hex[:8]}"
    chat_id = f"112233{uuid.uuid4().int % 10000}"

    await _link_user(db_session, user_id, chat_id)

    tx = await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=890.0,
        vendor_raw="NETFLIX SUBSCRIPTION",
        auto_categorize=True,
    )
    assert tx.status == TransactionStatus.NEEDS_REVIEW

    catchup_res = await dispatch_all_catchups(db_session, user_id=user_id)
    assert len(catchup_res["results"]) >= 1
    assert catchup_res["results"][0]["user_id"] == user_id

    cat_res = await process_telegram_update(
        db_session,
        {"message": {"chat": {"id": int(chat_id)}, "text": f"/cat {tx.id} Entertainment"}},
    )
    assert cat_res["status"] == "categorized"
    assert cat_res["category"] == "Entertainment"

    updated_tx = await get_transaction_by_id(db_session, user_id, tx.id)
    assert updated_tx.status == TransactionStatus.CATEGORIZED
