import uuid

import pytest

from app.db.models import TransactionStatus
from app.services.categorization import (
    create_or_update_vendor_rule,
    ensure_default_categories,
    matches_pattern,
)
from app.services.transactions import create_transaction, get_transaction_by_id


def test_matches_pattern():
    assert matches_pattern("swiggy", "UPI/SWIGGY/12345") is True
    assert matches_pattern("zomato|swiggy", "Zomato Order #88") is True
    assert matches_pattern("netflix", "Spotify Premium") is False


@pytest.mark.asyncio
async def test_categorization_flow_and_re_evaluation(db_session):
    user_id = f"test_cat_user_{uuid.uuid4().hex[:8]}"
    cats = await ensure_default_categories(db_session, user_id)
    food_cat = next((c for c in cats if "Food" in c.name), cats[0])

    # 1. Ingest transaction without rule -> NEEDS_REVIEW
    tx = await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=550.0,
        vendor_raw="UPI/SWIGGY/ORDER_123",
        auto_categorize=True,
    )
    assert tx.status == TransactionStatus.NEEDS_REVIEW
    assert tx.category_id is None

    # 2. Add rule for Swiggy -> should re-evaluate and mark as CATEGORIZED
    rule = await create_or_update_vendor_rule(
        db=db_session,
        user_id=user_id,
        vendor_pattern="swiggy",
        category_id=food_cat.id,
        re_evaluate_pending=True,
    )
    assert rule.default_category_id == food_cat.id

    refreshed_tx = await get_transaction_by_id(db_session, user_id, tx.id)
    assert refreshed_tx.status == TransactionStatus.CATEGORIZED
    assert refreshed_tx.category_id == food_cat.id

    # 3. Ingest next Swiggy transaction -> immediately CATEGORIZED
    tx2 = await create_transaction(
        db=db_session,
        user_id=user_id,
        amount=320.0,
        vendor_raw="SWIGGY_INSTAMART_456",
        auto_categorize=True,
    )
    assert tx2.status == TransactionStatus.CATEGORIZED
    assert tx2.category_id == food_cat.id
