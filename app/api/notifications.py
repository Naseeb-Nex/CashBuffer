from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.notifications import dispatch_all_catchups

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class CatchUpDispatchResponse(BaseModel):
    dispatched: int
    results: list[dict[str, Any]]


@router.post("/catch-up", response_model=CatchUpDispatchResponse, summary="Dispatch uncategorized catch-up reminders")
async def trigger_catchup(
    all_users: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    target_user = None if all_users else user_id
    result = await dispatch_all_catchups(db, target_user)
    return result
