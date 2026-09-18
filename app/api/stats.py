from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.stats import get_multi_account_stats

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/summary", summary="Multi-account aggregated financial summary")
async def get_multi_account_summary(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    """
    Returns financial statistics aggregated natively across all linked credentials (multi-account)
    since all transactions map to the user boundary.
    """
    return await get_multi_account_stats(db=db, user_id=user_id, start_date=start_date, end_date=end_date)
