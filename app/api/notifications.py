from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.notifications import dispatch_all_catchups

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class CatchUpDispatchResponse(BaseModel):
    dispatched: int
    results: list[dict[str, Any]]

@router.post("/catch-up", response_model=CatchUpDispatchResponse, summary="Dispatch uncategorized catch-up reminders")
async def trigger_catchup(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    result = await dispatch_all_catchups(repo, user_id)
    return result
