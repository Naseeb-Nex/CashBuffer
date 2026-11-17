import hashlib
import logging
from datetime import date
from typing import Any

from app.domain.models import Transaction, TransactionStatus
from app.email.parser import UnifiedBankParser
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.categorization import (
    categorize_transaction,
    ensure_default_categories,
    matches_pattern,
)

logger = logging.getLogger(__name__)

async def _ensure_user_exists(repo: NativeRepository, user_id: str) -> None:
    """Ensures user record exists in the database and has categories."""
    user = await repo.get_user_by_id(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)
        await ensure_default_categories(repo, user.id)

async def _validate_user_category(repo: NativeRepository, user_id: str, category_id: int | None) -> bool:
    """Confirms category_id exists and belongs to the given user."""
    if category_id is None:
        return True
    cat = await repo.get_category_by_id(user_id, category_id)
    return cat is not None

def _compute_tx_hash(
    user_id: str, amount: float, currency: str, is_inflow: bool, record_date: date, vendor_raw: str
) -> str:
    payload = f"{user_id}:{amount}:{currency}:{is_inflow}:{record_date.isoformat()}:{vendor_raw.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

async def create_transaction(
    db: NativeRepository,  # db parameter retains backward compat with test signatures
    user_id: str,
    amount: float,
    currency: str = "INR",
    is_inflow: bool = False,
    record_date: date | None = None,
    vendor_raw: str = "Unknown",
    category_id: int | None = None,
    auto_categorize: bool = True,
) -> Transaction:
    """Creates a new transaction for user with optional auto-categorization."""
    # Ensure user exists and get user internal UUID
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_or_create_user(user_id)
        await ensure_default_categories(db, user.id)
    internal_user_id = user.id

    if record_date is None:
        record_date = date.today()

    if category_id and not await _validate_user_category(db, internal_user_id, category_id):
        category_id = None

    tx_hash = _compute_tx_hash(internal_user_id, amount, currency, is_inflow, record_date, vendor_raw)

    existing_tx = await db.get_transaction_by_hash(tx_hash)
    if existing_tx:
        return existing_tx

    status = TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED
    tx = Transaction(
        id=0,
        user_id=internal_user_id,
        amount=amount,
        currency=currency,
        is_inflow=is_inflow,
        record_date=record_date,
        vendor_raw=vendor_raw,
        category_id=category_id,
        status=status,
        tx_hash=tx_hash,
        dedupe_hash=tx_hash,
    )

    if auto_categorize and not category_id:
        await categorize_transaction(db, tx)

    return await db.insert_transaction(tx)

async def create_batch_transactions(
    db: NativeRepository,
    user_id: str,
    items: list[dict[str, Any]],
    auto_categorize: bool = True,
) -> list[Transaction]:
    """Inserts a batch of transactions for user."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_or_create_user(user_id)
        await ensure_default_categories(db, user.id)
    internal_user_id = user.id

    rules = await db.get_vendor_rules(internal_user_id) if auto_categorize else []
    categories = await db.get_categories(internal_user_id)
    valid_category_ids = {c.id for c in categories}

    created: list[Transaction] = []
    seen_in_batch: dict[str, Transaction] = {}

    for item in items:
        rec_date = item.get("record_date")
        if isinstance(rec_date, str):
            rec_date = date.fromisoformat(rec_date)
        elif rec_date is None:
            rec_date = date.today()

        amount = float(item["amount"])
        currency = item.get("currency", "INR")
        is_inflow = bool(item.get("is_inflow", False))
        vendor_raw = str(item.get("vendor_raw", "Unknown"))
        category_id = item.get("category_id")

        if category_id and category_id not in valid_category_ids:
            category_id = None

        tx_hash = _compute_tx_hash(internal_user_id, amount, currency, is_inflow, rec_date, vendor_raw)

        if tx_hash in seen_in_batch:
            created.append(seen_in_batch[tx_hash])
            continue

        existing = await db.get_transaction_by_hash(tx_hash)
        if existing:
            seen_in_batch[tx_hash] = existing
            created.append(existing)
            continue

        status = TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED
        if auto_categorize and not category_id:
            matched_cat_id = None
            for rule in rules:
                if matches_pattern(rule.vendor_regex, vendor_raw):
                    matched_cat_id = rule.default_category_id
                    break
            if matched_cat_id is not None:
                category_id = matched_cat_id
                status = TransactionStatus.CATEGORIZED
            else:
                status = TransactionStatus.NEEDS_REVIEW

        tx = Transaction(
            id=0,
            user_id=internal_user_id,
            amount=amount,
            currency=currency,
            is_inflow=is_inflow,
            record_date=rec_date,
            vendor_raw=vendor_raw,
            category_id=category_id,
            status=status,
            tx_hash=tx_hash,
            dedupe_hash=tx_hash,
        )

        saved = await db.insert_transaction(tx)
        seen_in_batch[tx_hash] = saved
        created.append(saved)

    return created

async def ingest_from_raw_email(
    db: NativeRepository,
    user_id: str,
    email_text: str,
) -> Transaction | None:
    """Parses raw email text and creates a transaction."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_or_create_user(user_id)
    internal_user_id = user.id

    parsed = UnifiedBankParser.parse(email_text)
    if not parsed:
        quarantine = await db.add_quarantined_email(
            user_id=internal_user_id,
            email_text=email_text,
            error_reason="No parser matched or parsing completely failed",
        )

        if user.telegram_chat_id:
            try:
                from app.chat_connectors.telegram import telegram_connector

                alert_text = f"⚠️ *CashBuffer Error*: An email was received but could not be parsed. Quarantined (ID: {quarantine.id}) for review."
                await telegram_connector.send_message(user.telegram_chat_id, alert_text)
            except Exception as e:
                logger.warning("Failed to dispatch quarantine alert: %s", e)
        return None

    return await create_transaction(
        db=db,
        user_id=user_id,
        amount=parsed["amount"],
        currency=parsed["currency"],
        is_inflow=parsed["is_inflow"],
        record_date=parsed["record_date"],
        vendor_raw=parsed["vendor_raw"],
        auto_categorize=True,
    )

async def get_user_transactions(
    db: NativeRepository,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    status: TransactionStatus | None = None,
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> list[Transaction]:
    """Fetches user transactions scoped to internal user id."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return []
    return await db.list_transactions(
        user_id=user.id,
        limit=limit,
        offset=offset,
        status=status,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
    )

async def get_transaction_by_id(
    db: NativeRepository,
    user_id: str,
    transaction_id: int,
) -> Transaction | None:
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return None
    return await db.get_transaction_by_id(user.id, transaction_id)

async def update_transaction(
    db: NativeRepository,
    user_id: str,
    transaction_id: int,
    category_id: int | None = None,
    status: TransactionStatus | None = None,
    vendor_raw: str | None = None,
    amount: float | None = None,
) -> Transaction | None:
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return None

    if category_id is not None:
        if not await _validate_user_category(db, user.id, category_id):
            return None

    return await db.update_transaction(
        user_id=user.id,
        tx_id=transaction_id,
        category_id=category_id,
        status=status,
        vendor_raw=vendor_raw,
        amount=amount,
    )

async def delete_transaction(
    db: NativeRepository,
    user_id: str,
    transaction_id: int,
) -> bool:
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return False
    return await db.delete_transaction(user.id, transaction_id)

async def get_financial_summary(
    db: NativeRepository,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Aggregates inflows, outflows, balance, and spend by category."""
    user = await db.get_user_by_idp(user_id)
    if not user:
        user = await db.get_user_by_id(user_id)
    if not user:
        return {
            "total_inflow": 0.0,
            "total_outflow": 0.0,
            "net_buffer": 0.0,
            "transaction_count": 0,
            "uncategorized_count": 0,
            "category_breakdown": [],
            "linked_accounts_count": 0,
        }

    return await db.get_financial_summary(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
    )
