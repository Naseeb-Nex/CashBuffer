import hashlib
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, Transaction, TransactionStatus, User
from app.email.parser import UnifiedBankParser
from app.services.categorization import (
    categorize_transaction,
    ensure_default_categories,
)

logger = logging.getLogger(__name__)


async def _ensure_user_exists(db: AsyncSession, user_id: str) -> User:
    """Ensures user record exists in the database."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@cashbuffer.local")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await ensure_default_categories(db, user_id)
    return user


async def _validate_user_category(db: AsyncSession, user_id: str, category_id: int | None) -> bool:
    """Confirms category_id exists and belongs to the given user."""
    if category_id is None:
        return True
    stmt = select(Category).where(Category.user_id == user_id, Category.id == category_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


def _compute_tx_hash(
    user_id: str, amount: float, currency: str, is_inflow: bool, record_date: date, vendor_raw: str
) -> str:
    payload = f"{user_id}:{amount}:{currency}:{is_inflow}:{record_date.isoformat()}:{vendor_raw.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def create_transaction(
    db: AsyncSession,
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
    await _ensure_user_exists(db, user_id)

    if record_date is None:
        record_date = date.today()

    if category_id and not await _validate_user_category(db, user_id, category_id):
        category_id = None

    tx_hash = _compute_tx_hash(user_id, amount, currency, is_inflow, record_date, vendor_raw)

    # Check if transaction with this hash already exists
    stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
    existing_tx = (await db.execute(stmt)).scalar_one_or_none()
    if existing_tx:
        return existing_tx

    tx = Transaction(
        user_id=user_id,
        amount=amount,
        currency=currency,
        is_inflow=is_inflow,
        record_date=record_date,
        vendor_raw=vendor_raw,
        category_id=category_id,
        status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
        tx_hash=tx_hash,
    )

    if auto_categorize and not category_id:
        await categorize_transaction(db, tx)

    db.add(tx)
    try:
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        stmt = select(Transaction).where(Transaction.tx_hash == tx_hash)
        existing_tx = (await db.execute(stmt)).scalar_one_or_none()
        if existing_tx:
            return existing_tx
        raise


async def create_batch_transactions(
    db: AsyncSession,
    user_id: str,
    items: list[dict[str, Any]],
    auto_categorize: bool = True,
) -> list[Transaction]:
    """Inserts a batch of transactions for user."""
    await _ensure_user_exists(db, user_id)

    cat_stmt = select(Category.id).where(Category.user_id == user_id)
    cat_res = await db.execute(cat_stmt)
    valid_category_ids = set(cat_res.scalars().all())

    rules = []
    if auto_categorize:
        from app.db.models import VendorRule
        from app.services.categorization import matches_pattern

        rules_stmt = select(VendorRule).where(VendorRule.user_id == user_id)
        rules_res = await db.execute(rules_stmt)
        rules = rules_res.scalars().all()

    processed_items = []
    tx_hashes = []
    for item in items:
        rec_date = item.get("record_date")
        if isinstance(rec_date, str):
            try:
                rec_date = datetime.strptime(rec_date, "%Y-%m-%d").date()
            except ValueError:
                rec_date = date.today()
        elif rec_date is None:
            rec_date = date.today()

        amount = float(item["amount"])
        currency = item.get("currency", "INR")
        is_inflow = bool(item.get("is_inflow", False))
        vendor_raw = str(item.get("vendor_raw", "Unknown"))
        tx_hash = _compute_tx_hash(user_id, amount, currency, is_inflow, rec_date, vendor_raw)

        tx_hashes.append(tx_hash)
        processed_items.append(
            {
                "original": item,
                "record_date": rec_date,
                "amount": amount,
                "currency": currency,
                "is_inflow": is_inflow,
                "vendor_raw": vendor_raw,
                "tx_hash": tx_hash,
            }
        )

    existing_records = []
    if tx_hashes:
        stmt = select(Transaction).where(Transaction.tx_hash.in_(tx_hashes))
        res = await db.execute(stmt)
        existing_records = res.scalars().all()

    existing_by_hash = {tx.tx_hash: tx for tx in existing_records}

    created: list[Transaction] = []
    to_add: list[Transaction] = []
    seen_in_batch = set()

    for p_item in processed_items:
        tx_hash = p_item["tx_hash"]

        if tx_hash in existing_by_hash:
            created.append(existing_by_hash[tx_hash])
            continue

        if tx_hash in seen_in_batch:
            for t in to_add:
                if t.tx_hash == tx_hash:
                    created.append(t)
                    break
            continue

        category_id = p_item["original"].get("category_id")
        if category_id and category_id not in valid_category_ids:
            category_id = None

        tx = Transaction(
            user_id=user_id,
            amount=p_item["amount"],
            currency=p_item["currency"],
            is_inflow=p_item["is_inflow"],
            record_date=p_item["record_date"],
            vendor_raw=p_item["vendor_raw"],
            category_id=category_id,
            status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
            tx_hash=tx_hash,
        )

        if auto_categorize and not category_id:
            matched_cat_id = None
            for rule in rules:
                if matches_pattern(rule.vendor_regex, tx.vendor_raw):
                    matched_cat_id = rule.default_category_id
                    break
            if matched_cat_id is not None:
                tx.category_id = matched_cat_id
                tx.status = TransactionStatus.CATEGORIZED
            else:
                tx.status = TransactionStatus.NEEDS_REVIEW

        to_add.append(tx)
        created.append(tx)
        seen_in_batch.add(tx_hash)

    if to_add:
        db.add_all(to_add)
        try:
            await db.commit()
            for tx in to_add:
                await db.refresh(tx)
        except IntegrityError:
            await db.rollback()
            stmt = select(Transaction).where(Transaction.tx_hash.in_(tx_hashes))
            res = await db.execute(stmt)
            all_existing = res.scalars().all()
            by_hash = {t.tx_hash: t for t in all_existing}
            return [by_hash[h] for h in tx_hashes if h in by_hash]

    return created


async def create_transaction_from_parsed(
    db: AsyncSession,
    user_id: str,
    parsed: dict[str, Any],
) -> Transaction:
    """Creates a transaction from parsed bank alert dict."""
    return await create_transaction(
        db=db,
        user_id=user_id,
        amount=parsed["amount"],
        currency=parsed.get("currency", "INR"),
        is_inflow=parsed.get("is_inflow", False),
        record_date=parsed.get("record_date"),
        vendor_raw=parsed.get("vendor_raw", "Unknown"),
        auto_categorize=True,
    )


async def ingest_from_raw_email(
    db: AsyncSession,
    user_id: str,
    email_text: str,
) -> Transaction | None:
    """Parses raw email text and creates a transaction."""
    parsed = UnifiedBankParser.parse(email_text)
    if not parsed:
        from app.db.models import QuarantinedEmail

        quarantine = QuarantinedEmail(
            user_id=user_id, email_text=email_text, error_reason="No parser matched or parsing completely failed"
        )
        db.add(quarantine)
        await db.commit()

        user = await db.get(User, user_id)
        if user and user.telegram_chat_id:
            try:
                from app.chat_connectors.telegram import telegram_connector

                alert_text = f"⚠️ *CashBuffer Error*: An email was received but could not be parsed. Quarantined (ID: {quarantine.id}) for review."
                await telegram_connector.send_message(user.telegram_chat_id, alert_text)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning("Failed to dispatch quarantine alert: %s", e)
        else:
            import logging

            logging.getLogger(__name__).info("Email quarantined, but user has no Telegram linked for alerts.")

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
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    status: TransactionStatus | None = None,
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> list[Transaction]:
    """Fetches filtered transactions for the given tenant."""
    stmt = select(Transaction).where(Transaction.user_id == user_id)

    if status:
        stmt = stmt.where(Transaction.status == status)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if start_date:
        stmt = stmt.where(Transaction.record_date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.record_date <= end_date)
    if search:
        stmt = stmt.where(Transaction.vendor_raw.ilike(f"%{search}%"))

    stmt = stmt.order_by(Transaction.record_date.desc(), Transaction.id.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_transaction_by_id(db: AsyncSession, user_id: str, transaction_id: int) -> Transaction | None:
    stmt = select(Transaction).where(Transaction.user_id == user_id, Transaction.id == transaction_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_transaction(
    db: AsyncSession,
    user_id: str,
    transaction_id: int,
    category_id: int | None = None,
    status: TransactionStatus | None = None,
    vendor_raw: str | None = None,
    amount: float | None = None,
) -> Transaction | None:
    tx = await get_transaction_by_id(db, user_id, transaction_id)
    if not tx:
        return None

    if category_id is not None:
        if not await _validate_user_category(db, user_id, category_id):
            return None
        tx.category_id = category_id
        tx.status = TransactionStatus.CATEGORIZED
    if status is not None:
        tx.status = status
    if vendor_raw is not None:
        tx.vendor_raw = vendor_raw
    if amount is not None:
        tx.amount = amount

    await db.commit()
    await db.refresh(tx)
    return tx


async def delete_transaction(db: AsyncSession, user_id: str, transaction_id: int) -> bool:
    stmt = delete(Transaction).where(Transaction.user_id == user_id, Transaction.id == transaction_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_financial_summary(
    db: AsyncSession,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Aggregates inflows, outflows, balance, and spend by category."""
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if start_date:
        stmt = stmt.where(Transaction.record_date >= start_date)
    if end_date:
        stmt = stmt.where(Transaction.record_date <= end_date)

    result = await db.execute(stmt)
    transactions = result.scalars().all()

    total_inflow = 0.0
    total_outflow = 0.0
    uncategorized_count = 0
    category_totals: dict[int | None, float] = {}

    for tx in transactions:
        if tx.is_inflow:
            total_inflow += tx.amount
        else:
            total_outflow += tx.amount
            cat_key = tx.category_id
            category_totals[cat_key] = category_totals.get(cat_key, 0.0) + tx.amount

        if tx.status != TransactionStatus.CATEGORIZED or tx.category_id is None:
            uncategorized_count += 1

    # Fetch category names
    cat_stmt = select(Category).where(Category.user_id == user_id)
    cat_res = await db.execute(cat_stmt)
    categories = {c.id: c.name for c in cat_res.scalars().all()}

    breakdown = []
    for cat_id, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        cat_name = categories.get(cat_id, "Uncategorized") if cat_id else "Uncategorized"
        breakdown.append({"category_id": cat_id, "category_name": cat_name, "total_amount": round(amt, 2)})

    return {
        "total_inflow": round(total_inflow, 2),
        "total_outflow": round(total_outflow, 2),
        "net_buffer": round(total_inflow - total_outflow, 2),
        "transaction_count": len(transactions),
        "uncategorized_count": uncategorized_count,
        "category_breakdown": breakdown,
    }
