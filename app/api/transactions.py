from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.domain.models import TransactionStatus
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.transactions import (
    delete_transaction,
    get_financial_summary,
    get_transaction_by_id,
    get_user_transactions,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

class TransactionResponse(BaseModel):
    id: int
    user_id: str
    amount: float
    currency: str
    is_inflow: bool
    record_date: str
    vendor_raw: str
    category_id: int | None = None
    status: TransactionStatus

    model_config = {"from_attributes": True}

class CategoryBreakdownItem(BaseModel):
    category_id: int | None
    category_name: str
    total_amount: float

class FinancialSummary(BaseModel):
    total_inflow: float
    total_outflow: float
    net_buffer: float
    transaction_count: int
    uncategorized_count: int
    category_breakdown: list[CategoryBreakdownItem]
    linked_accounts_count: int

class UpdateTransactionRequest(BaseModel):
    category_id: int | None = None
    status: TransactionStatus | None = None
    vendor_raw: str | None = None
    amount: float | None = None

def _to_response(tx) -> TransactionResponse:
    rec_date_str = tx.record_date.isoformat() if hasattr(tx.record_date, "isoformat") else str(tx.record_date)
    return TransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        amount=tx.amount,
        currency=tx.currency,
        is_inflow=tx.is_inflow,
        record_date=rec_date_str,
        vendor_raw=tx.vendor_raw,
        category_id=tx.category_id,
        status=tx.status,
    )

@router.get("", response_model=list[TransactionResponse], summary="Get user transactions")
async def list_transactions(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: TransactionStatus | None = Query(None, alias="status"),
    category_id: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    search: str | None = Query(None),
    min_amount: float | None = Query(None),
    max_amount: float | None = Query(None),
):
    from datetime import date
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None

    txs = await get_user_transactions(
        db=repo,
        user_id=user_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        category_id=category_id,
        start_date=sd,
        end_date=ed,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    return [_to_response(t) for t in txs]

@router.get("/summary", response_model=FinancialSummary, summary="Get aggregate financial summary")
async def get_summary(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
):
    from datetime import date
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None

    return await get_financial_summary(
        db=repo,
        user_id=user_id,
        start_date=sd,
        end_date=ed,
    )

@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get single transaction")
async def get_single_transaction(
    transaction_id: int,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    tx = await get_transaction_by_id(db=repo, user_id=user_id, transaction_id=transaction_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _to_response(tx)

@router.patch("/{transaction_id}", response_model=TransactionResponse, summary="Update transaction")
async def patch_transaction(
    transaction_id: int,
    payload: UpdateTransactionRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    tx = await update_transaction(
        db=repo,
        user_id=user_id,
        transaction_id=transaction_id,
        category_id=payload.category_id,
        status=payload.status,
        vendor_raw=payload.vendor_raw,
        amount=payload.amount,
    )
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or invalid category",
        )
    return _to_response(tx)

@router.delete("/{transaction_id}", summary="Delete transaction")
async def remove_transaction(
    transaction_id: int,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    success = await delete_transaction(db=repo, user_id=user_id, transaction_id=transaction_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return {"status": "success", "deleted_id": transaction_id}
