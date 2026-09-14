from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
        if data.telegram_chat_id:
            user.telegram_chat_id = data.telegram_chat_id
    await db.commit()
    return {"status": "ok", "user_id": user_id}

@router.post("/transactions")
async def ingest_transactions(
    transactions: List[TransactionIngestSchema],
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk ingest purely parsed transactions."""
    ingested = []
    for tx_data in transactions:
        tx = await create_transaction_from_parsed(db, user_id, tx_data.model_dump())
        ingested.append(tx.id)
    return {"status": "ok", "ingested_count": len(ingested), "ids": ingested}

@router.post("/categories")
async def ingest_categories(
    categories: List[CategoryIngestSchema],
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk ingest categories."""
    new_cats = []
    for cat_data in categories:
        cat = Category(
            user_id=user_id,
            name=cat_data.name,
            parent_id=cat_data.parent_id
        )
        db.add(cat)
        new_cats.append(cat)
    await db.commit()
    return {"status": "ok", "ingested_count": len(new_cats)}
