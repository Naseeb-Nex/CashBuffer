import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, select
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

    tx = Transaction(
        user_id=user_id,
        amount=amount,
        currency=currency,
        is_inflow=is_inflow,
        record_date=record_date,
        vendor_raw=vendor_raw,
        category_id=category_id,
        status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
    )

    if auto_categorize and not category_id:
        await categorize_transaction(db, tx)

    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def create_batch_transactions(
    db: AsyncSession,
    user_id: str,
    items: list[dict[str, Any]],
    auto_categorize: bool = True,
) -> list[Transaction]:
    """Inserts a batch of transactions for user."""
    await _ensure_user_exists(db, user_id)

    created: list[Transaction] = []
    for item in items:
        rec_date = item.get("record_date")
        if isinstance(rec_date, str):
            try:
                rec_date = datetime.strptime(rec_date, "%Y-%m-%d").date()
            except ValueError:
                rec_date = date.today()
        elif rec_date is None:
            rec_date = date.today()

        category_id = item.get("category_id")
        tx = Transaction(
            user_id=user_id,
            amount=float(item["amount"]),
            currency=item.get("currency", "INR"),
            is_inflow=bool(item.get("is_inflow", False)),
            record_date=rec_date,
            vendor_raw=str(item.get("vendor_raw", "Unknown")),
            category_id=category_id,
            status=TransactionStatus.CATEGORIZED if category_id else TransactionStatus.PARSED,
        )
        if auto_categorize and not category_id:
            await categorize_transaction(db, tx)

        db.add(tx)
        created.append(tx)

    await db.commit()
    for tx in created:
        await db.refresh(tx)
    return created


async def ingest_from_raw_email(
    db: AsyncSession,
    user_id: str,
    email_text: str,
) -> Transaction | None:
    """Parses raw email text and creates a transaction."""
    parsed = UnifiedBankParser.parse(email_text)
    if not parsed:
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
