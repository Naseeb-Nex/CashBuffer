from datetime import date, datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import get_current_user
from app.api.transactions import TransactionResponse, _to_response
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.categorization import batch_re_evaluate_transactions
from app.services.transactions import (
    create_batch_transactions,
    create_transaction,
    ingest_from_raw_email,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

class DirectIngestItem(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    is_inflow: bool = False
    record_date: date | None = None
    vendor_raw: str = Field(..., min_length=1)
    category_id: int | None = None
    auto_categorize: bool = True

class BatchIngestRequest(BaseModel):
    transactions: list[DirectIngestItem]
    auto_categorize: bool = True

class EmailWebhookRequest(BaseModel):
    email_text: str = Field(..., min_length=5)

@router.post("/direct", response_model=TransactionResponse, summary="Direct transaction ingestion")
async def ingest_direct(
    payload: DirectIngestItem,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    tx = await create_transaction(
        db=repo,
        user_id=user_id,
        amount=payload.amount,
        currency=payload.currency,
        is_inflow=payload.is_inflow,
        record_date=payload.record_date,
        vendor_raw=payload.vendor_raw,
        category_id=payload.category_id,
        auto_categorize=payload.auto_categorize,
    )
    return _to_response(tx)

@router.post("/batch", response_model=list[TransactionResponse], summary="Batch transaction ingestion")
async def ingest_batch(
    payload: BatchIngestRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    items = [item.model_dump() for item in payload.transactions]
    created = await create_batch_transactions(
        db=repo,
        user_id=user_id,
        items=items,
        auto_categorize=payload.auto_categorize,
    )
    return [_to_response(t) for t in created]

@router.post("/email-webhook", summary="Ingest raw transaction email alert")
async def ingest_email_webhook(
    payload: EmailWebhookRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    tx = await ingest_from_raw_email(db=repo, user_id=user_id, email_text=payload.email_text)
    if not tx:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "quarantined", "detail": "Message safely queued for manual review"},
        )
    return _to_response(tx)

@router.post("/re-evaluate", summary="Re-evaluate all pending transactions against current rules")
async def re_evaluate_rules(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)
    count = await batch_re_evaluate_transactions(repo=repo, user_id=user.id)
    return {"status": "success", "user_id": user_id, "updated_count": count}

class QuarantinedEmailResponse(BaseModel):
    id: int
    user_id: str | None = None
    email_text: str
    error_reason: str
    created_at: datetime | None = None
    resolved: bool

    model_config = ConfigDict(from_attributes=True)

@router.get("/quarantine", response_model=list[QuarantinedEmailResponse], summary="Get quarantined emails")
async def get_quarantined_emails(
    resolved: bool | None = None,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_or_create_user(user_id)

    quarantined = await repo.get_quarantined_emails(user_id=user.id, resolved=resolved)
    return [
        QuarantinedEmailResponse(
            id=q.id,
            user_id=q.user_id,
            email_text=q.email_text,
            error_reason=q.error_reason,
            created_at=q.created_at,
            resolved=q.resolved,
        )
        for q in quarantined
    ]
