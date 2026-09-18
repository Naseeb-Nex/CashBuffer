import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.export import format_budget, format_transactions
from app.services.transactions import get_financial_summary, get_user_transactions

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/transactions", summary="Export transaction history")
async def export_transactions(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    format: str | None = Query("json", pattern="^(csv|json)$"),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export transaction history for the given date range.
    """
    transactions = await get_user_transactions(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000,  # Large limit instead of pagination for export
        offset=0,
    )

    if format == "csv":
        csv_data = format_transactions(transactions, "csv")
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )

    # For JSON format, model instances need to be serialized
    json_data = format_transactions(transactions, "json")
    return StreamingResponse(
        io.StringIO(json_data),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=transactions.json"},
    )


@router.get("/budget", summary="Export budget summary")
async def export_budget(
    format: str = Query("json", pattern="^(csv|json)$"),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export budget summary.
    """
    summary = await get_financial_summary(db=db, user_id=user_id)

    if format == "csv":
        csv_data = format_budget(summary, "csv")
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=budget.csv"},
        )

    json_data = format_budget(summary, "json")
    return StreamingResponse(
        io.StringIO(json_data),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=budget.json"},
    )
