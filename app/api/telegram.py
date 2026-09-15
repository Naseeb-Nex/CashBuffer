from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
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
