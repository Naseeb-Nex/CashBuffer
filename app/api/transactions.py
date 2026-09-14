from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.database import get_db
from app.db.models import Transaction
from app.api.auth import get_current_user

router = APIRouter(tags=["Transactions"])

@router.get("/transactions", summary="Get user transactions")
async def get_transactions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> List[dict]:
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "currency": t.currency,
            "is_inflow": t.is_inflow,
            "record_date": str(t.record_date),
            "vendor_raw": t.vendor_raw,
            "status": t.status
        }
        for t in transactions
    ]
