import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.export import format_budget, format_transactions
from app.services.transactions import get_financial_summary, get_user_transactions

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/transactions", summary="Export transaction history")
async def export_transactions(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    format: str | None = Query("json", pattern="^(csv|json)$"),
    user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
):
    transactions = await get_user_transactions(
        db=repo,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0,
    )

    if format == "csv":
        csv_data = format_transactions(transactions, "csv")
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )

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
    repo: NativeRepository = Depends(get_repository),
):
    summary = await get_financial_summary(db=repo, user_id=user_id)

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
