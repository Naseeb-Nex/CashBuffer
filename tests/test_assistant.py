import uuid

import pytest

from app.db.models import TransactionStatus
from app.services.assistant import execute_assistant_chat, get_assistant_context
from app.services.transactions import create_transaction


@pytest.mark.asyncio
async def test_assistant_context_and_deterministic_chat(db_session):
    user_id = f"test_assistant_user_{uuid.uuid4().hex[:8]}"

    # Create inflow and outflow
    await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=10000.0,
        is_inflow=True,
        vendor_raw="Salary Credit",
    )
    await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=2500.0,
        is_inflow=False,
        vendor_raw="Grocery Store",
    )

    context = await get_assistant_context(db_session, user_id)
    assert context["summary"]["total_inflow"] == 10000.0
    assert context["summary"]["total_outflow"] == 2500.0
    assert context["summary"]["net_buffer"] == 7500.0

    # Test deterministic query for buffer/balance
    res = await execute_assistant_chat(
        db=db_session,
        user_id=user_id,
        message="What is my current net cash buffer and balance?",
    )
    assert "7500.00" in res["reply"]
    assert len(res["widgets"]) > 0
    assert res["widgets"][0]["type"] == "summary_card"


@pytest.mark.asyncio
async def test_assistant_uncategorized_query(db_session):
    user_id = f"test_assistant_user_{uuid.uuid4().hex[:8]}"

    tx = await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=750.0,
        vendor_raw="Mystery Vendor Store",
        auto_categorize=True,
    )
    assert tx.status == TransactionStatus.NEEDS_REVIEW

    res = await execute_assistant_chat(
        db=db_session,
        user_id=user_id,
        message="Show me pending uncategorized transactions needing review",
    )
    assert "Mystery Vendor Store" in res["reply"]
    assert any(w["type"] == "uncategorized_list" for w in res["widgets"])
