from datetime import date
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import OAuthCredential
from app.services.transactions import get_financial_summary

async def get_multi_account_stats(
    db: AsyncSession,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Computes stats natively aggregating across all linked auth sources."""
    # Base transaction stats natively aggregate across all accounts due to multi-tenant boundary
    base_summary = await get_financial_summary(db=db, user_id=user_id, start_date=start_date, end_date=end_date)
    
    # Linked accounts count
    stmt = select(func.count(OAuthCredential.id)).where(OAuthCredential.user_id == user_id, OAuthCredential.is_valid == True)
    res = await db.execute(stmt)
    linked_accounts = res.scalar() or 0
    
    return {
        **base_summary,
        "linked_accounts_count": linked_accounts
    }
