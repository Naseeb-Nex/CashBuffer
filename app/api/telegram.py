from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.notifications import process_telegram_update

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/webhook", summary="Telegram Bot Webhook endpoint")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    update_data: dict[str, Any] = await request.json()
    result = await process_telegram_update(db, update_data)
    return {"ok": True, "result": result}


@router.post("/unlink", summary="Unlink telegram chat ID")
async def unlink_telegram(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = update(User).where(User.id == user_id).values(telegram_chat_id=None)
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}
