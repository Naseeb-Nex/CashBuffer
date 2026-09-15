import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, Transaction, TransactionStatus, User, VendorRule

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Housing & Rent",
    "Utilities & Bills",
    "Transportation & Travel",
    "Shopping & Retail",
    "Entertainment & Leisure",
    "Healthcare & Fitness",
    "Salary & Income",
    "Investments",
    "Miscellaneous",
]


async def ensure_user_and_categories(db: AsyncSession, user_id: str) -> list[Category]:
    """Ensures user exists and has baseline categories available."""
    stmt_user = select(User).where(User.id == user_id)
    user_res = await db.execute(stmt_user)
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@cashbuffer.local")
        db.add(user)
        await db.commit()

    stmt = select(Category).where(Category.user_id == user_id)
    result = await db.execute(stmt)
    existing = result.scalars().all()
    if existing:
        return list(existing)

    categories = [Category(user_id=user_id, name=cat_name) for cat_name in DEFAULT_CATEGORIES]
    db.add_all(categories)
    await db.commit()
    for cat in categories:
        await db.refresh(cat)
    return categories


async def ensure_default_categories(db: AsyncSession, user_id: str) -> list[Category]:
    return await ensure_user_and_categories(db, user_id)


def matches_pattern(pattern: str, vendor_text: str) -> bool:
    """
    Checks if a vendor_text matches the pattern via regex, substring, or keyword match.
    """
    if not pattern or not vendor_text:
        return False
    text = vendor_text.strip().lower()
    pat = pattern.strip().lower()

    # Exact or substring match
    if pat in text or text in pat:
        return True

    # Try compiled regex
    try:
        if re.search(pattern, vendor_text, re.IGNORECASE):
            return True
    except re.error:
        pass

    return False


async def match_vendor_rule(db: AsyncSession, user_id: str, vendor_raw: str) -> tuple[int | None, str | None]:
    """
    Matches raw vendor string against user's stored vendor rules.
    Returns (default_category_id, matched_pattern) or (None, None).
    """
    stmt = select(VendorRule).where(VendorRule.user_id == user_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()

    for rule in rules:
        if matches_pattern(rule.vendor_regex, vendor_raw):
            return rule.default_category_id, rule.vendor_regex

    return None, None


async def categorize_transaction(db: AsyncSession, transaction: Transaction) -> Transaction:
    """
    Attempts autonomous categorization for a single transaction.
    """
    category_id, _ = await match_vendor_rule(db=db, user_id=transaction.user_id, vendor_raw=transaction.vendor_raw)

    if category_id is not None:
        transaction.category_id = category_id
        transaction.status = TransactionStatus.CATEGORIZED
    else:
        # If no rule matched, mark for proactive catch-up / review
        transaction.status = TransactionStatus.NEEDS_REVIEW

    return transaction


async def create_or_update_vendor_rule(
    db: AsyncSession,
    user_id: str,
    vendor_pattern: str,
    category_id: int,
    re_evaluate_pending: bool = True,
) -> VendorRule:
    """
    Creates/updates a vendor rule and optionally re-evaluates all pending transactions.
    """
    await ensure_user_and_categories(db, user_id)
    clean_pattern = vendor_pattern.strip()

    stmt = select(VendorRule).where(
        VendorRule.user_id == user_id,
        VendorRule.vendor_regex == clean_pattern,
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule:
        rule.default_category_id = category_id
    else:
        rule = VendorRule(
            user_id=user_id,
            vendor_regex=clean_pattern,
            default_category_id=category_id,
        )
        db.add(rule)

    await db.commit()
    await db.refresh(rule)

    if re_evaluate_pending:
        await batch_re_evaluate_transactions(db, user_id)

    return rule


async def batch_re_evaluate_transactions(db: AsyncSession, user_id: str) -> int:
    """
    Re-evaluates all NEEDS_REVIEW or PARSED transactions for a user against latest rules.
    Returns number of newly categorized transactions.
    """
    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.status.in_([TransactionStatus.PARSED, TransactionStatus.NEEDS_REVIEW]),
    )
    result = await db.execute(stmt)
    pending = result.scalars().all()

    rules_stmt = select(VendorRule).where(VendorRule.user_id == user_id)
    rules_result = await db.execute(rules_stmt)
    rules = rules_result.scalars().all()

    updated_count = 0
    for tx in pending:
        matched_cat_id = None
        for rule in rules:
            if matches_pattern(rule.vendor_regex, tx.vendor_raw):
                matched_cat_id = rule.default_category_id
                break

        if matched_cat_id is not None:
            tx.category_id = matched_cat_id
            tx.status = TransactionStatus.CATEGORIZED
            updated_count += 1

    if updated_count > 0:
        await db.commit()

    return updated_count
