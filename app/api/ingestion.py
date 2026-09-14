from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db
from app.db.models import Transaction, User, Category, TransactionStatus
from app.api.auth import get_current_user
from app.services.transactions import create_transaction_from_parsed

router = APIRouter()

class UserIngestParams(BaseModel):
    email: str
    telegram_chat_id: Optional[str] = None

class TransactionIngestSchema(BaseModel):
    amount: float
    currency: str = "USD"
    is_inflow: bool
    record_date: date
    vendor_raw: str

class CategoryIngestSchema(BaseModel):
    name: str
    parent_id: Optional[int] = None

@router.post("/user")
async def ingest_user(
    data: UserIngestParams,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync the Kinde user into the local database boundary table."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=data.email, telegram_chat_id=data.telegram_chat_id)
        db.add(user)
    else:
        user.email = data.email
        if data.telegram_chat_id is not None:
            user.telegram_chat_id = data.telegram_chat_id
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use")
    return {"status": "ok", "user_id": user_id}

@router.post("/transactions")
async def ingest_transactions(
    transactions: List[TransactionIngestSchema],
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk ingest purely parsed transactions."""
    ingested_txs = []
    for tx_data in transactions:
        tx = await create_transaction_from_parsed(db, user_id, tx_data.model_dump(), commit=False)
        ingested_txs.append(tx)
    await db.flush()
    ingested_ids = [tx.id for tx in ingested_txs]
    await db.commit()
    return {"status": "ok", "ingested_count": len(ingested_ids), "ids": ingested_ids}

@router.post("/categories")
async def ingest_categories(
    categories: List[CategoryIngestSchema],
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk ingest categories."""
    parent_ids = {cat_data.parent_id for cat_data in categories if cat_data.parent_id is not None}
    if parent_ids:
        result = await db.execute(select(Category.id).where(Category.id.in_(parent_ids), Category.user_id == user_id))
        valid_parent_ids = set(result.scalars().all())
        for pid in parent_ids:
            if pid not in valid_parent_ids:
                raise HTTPException(status_code=403, detail=f"Parent category {pid} not found or does not belong to user")

    new_cats = []
    for cat_data in categories:
        cat = Category(
            user_id=user_id,
            name=cat_data.name,
            parent_id=cat_data.parent_id
        )
        db.add(cat)
        new_cats.append(cat)

    await db.flush()
    ingested_ids = [cat.id for cat in new_cats]
    await db.commit()
    return {"status": "ok", "ingested_count": len(new_cats), "ids": ingested_ids}
