from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.notifications import process_telegram_update

router = APIRouter(prefix="/telegram", tags=["Telegram"])

@router.post("/webhook", summary="Telegram Bot Webhook endpoint")
async def telegram_webhook(
    request: Request,
    repo: NativeRepository = Depends(get_repository),
):
    update_data: dict[str, Any] = await request.json()
    result = await process_telegram_update(repo, update_data)
    return {"ok": True, "result": result}

@router.post("/unlink", summary="Unlink telegram chat ID")
async def unlink_telegram(
    user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
):
    user = await repo.get_user_by_idp(user_id)
    if not user:
        user = await repo.get_user_by_id(user_id)
    if user:
        await repo.set_telegram_chat_id(user.id, None)
    return {"ok": True}
