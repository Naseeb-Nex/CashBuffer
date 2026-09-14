
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Transaction

router = APIRouter(tags=["Transactions"])

@router.get("/transactions", summary="Get user transactions")
async def get_transactions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> list[dict]:
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
