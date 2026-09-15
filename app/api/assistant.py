from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.services.assistant import execute_assistant_chat

router = APIRouter(prefix="/assistant", tags=["Assistant"])


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class AssistantChatResponse(BaseModel):
    reply: str
    actions_executed: list[str] = []
    widgets: list[dict[str, Any]] = []
    context: dict[str, Any] = {}


@router.post("/chat", response_model=AssistantChatResponse, summary="Chat with AI Financial Assistant")
async def chat_with_assistant(
    payload: AssistantChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await execute_assistant_chat(
        db=db,
        user_id=user_id,
        message=payload.message,
    )
    return result
