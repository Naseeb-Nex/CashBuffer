from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import TransactionStatus
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
    record_date: date
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


@router.get("", response_model=list[TransactionResponse], summary="Get user transactions")
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: TransactionStatus | None = Query(None, alias="status"),
    category_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
):
    return await get_user_transactions(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


@router.get("/summary", response_model=FinancialSummary, summary="Get user financial summary and category breakdown")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    return await get_financial_summary(db=db, user_id=user_id, start_date=start_date, end_date=end_date)


@router.get("/{transaction_id}", response_model=TransactionResponse, summary="Get single transaction")
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    tx = await get_transaction_by_id(db=db, user_id=user_id, transaction_id=transaction_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx


@router.put("/{transaction_id}", response_model=TransactionResponse, summary="Update transaction")
async def edit_transaction(
    transaction_id: int,
    payload: UpdateTransactionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    tx = await update_transaction(
        db=db,
        user_id=user_id,
        transaction_id=transaction_id,
        category_id=payload.category_id,
        status=payload.status,
        vendor_raw=payload.vendor_raw,
        amount=payload.amount,
    )
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx


@router.delete("/{transaction_id}", summary="Delete transaction")
async def remove_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    success = await delete_transaction(db=db, user_id=user_id, transaction_id=transaction_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return {"status": "deleted", "id": transaction_id}
