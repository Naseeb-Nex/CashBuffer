import logging
import re

from app.domain.models import Category, Transaction, TransactionStatus, VendorRule
from app.infrastructure.persistence.native_repository import NativeRepository

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

async def ensure_user_and_categories(repo: NativeRepository, user_id: str) -> list[Category]:
    """Ensures user exists and has baseline categories available."""
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_user_by_id(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    internal_user_id = user.id
    existing = await repo.get_categories(internal_user_id)
    if existing:
        return existing

    created = []
    for cat_name in DEFAULT_CATEGORIES:
        c = await repo.create_category(user_id=internal_user_id, name=cat_name)
        created.append(c)
    return created

async def ensure_default_categories(repo: NativeRepository, user_id: str) -> list[Category]:
    return await ensure_user_and_categories(repo, user_id)

def matches_pattern(pattern: str, vendor_text: str) -> bool:
    """Checks if a vendor_text matches the pattern via regex or case-insensitive substring."""
    if not pattern or not vendor_text:
        return False
    text = vendor_text.strip().lower()
    pat = pattern.strip().lower()

    if pat in text or text in pat:
        return True

    try:
        if re.search(pattern, vendor_text, re.IGNORECASE):
            return True
    except re.error:
        pass
    return False

async def categorize_transaction(repo: NativeRepository, transaction: Transaction) -> Transaction:
    """Evaluates transaction vendor against user's vendor rules."""
    rules = await repo.get_vendor_rules(transaction.user_id)
    for rule in rules:
        if matches_pattern(rule.vendor_regex, transaction.vendor_raw):
            transaction.category_id = rule.default_category_id
            transaction.status = TransactionStatus.CATEGORIZED
            return transaction

    transaction.status = TransactionStatus.NEEDS_REVIEW
    return transaction

async def create_or_update_vendor_rule(
    repo: NativeRepository,
    user_id: str,
    vendor_pattern: str,
    category_id: int,
    re_evaluate_pending: bool = True,
) -> VendorRule:
    """Saves vendor rule and optionally re-evaluates all pending transactions."""
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_user_by_id(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)
    internal_user_id = user.id

    rule = await repo.upsert_vendor_rule(internal_user_id, vendor_pattern, category_id)

    if re_evaluate_pending:
        txs = await repo.list_transactions(user_id=internal_user_id, limit=500)
        for tx in txs:
            if tx.status in (TransactionStatus.PARSED, TransactionStatus.NEEDS_REVIEW):
                if matches_pattern(vendor_pattern, tx.vendor_raw):
                    await repo.update_transaction(
                        user_id=internal_user_id,
                        tx_id=tx.id,
                        category_id=category_id,
                        status=TransactionStatus.CATEGORIZED,
                    )
    return rule

async def batch_re_evaluate_transactions(repo: NativeRepository, user_id: str) -> int:
    """Re-runs all vendor rules against pending transactions for user."""
    rules = await repo.get_vendor_rules(user_id)
    if not rules:
        return 0

    txs = await repo.list_transactions(user_id=user_id, limit=500)
    updated = 0
    for tx in txs:
        if tx.status in (TransactionStatus.PARSED, TransactionStatus.NEEDS_REVIEW):
            for rule in rules:
                if matches_pattern(rule.vendor_regex, tx.vendor_raw):
                    await repo.update_transaction(
                        user_id=user_id,
                        tx_id=tx.id,
                        category_id=rule.default_category_id,
                        status=TransactionStatus.CATEGORIZED,
                    )
                    updated += 1
                    break
    return updated
