
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Transaction, TransactionStatus

router = APIRouter(tags=["Transactions"])

class TransactionResponse(BaseModel):
    id: int
    amount: float
    currency: str
    is_inflow: bool
    record_date: date
    vendor_raw: str
    category_id: int | None = None
    status: TransactionStatus

    model_config = {"from_attributes": True}

@router.get("/transactions", summary="Get user transactions", response_model=list[TransactionResponse])
async def get_transactions(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.record_date.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()

    return transactions
