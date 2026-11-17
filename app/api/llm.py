from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.llm import (
    get_user_llm_config,
    save_user_llm_config,
    test_llm_connection,
)

router = APIRouter(prefix="/llm-config", tags=["BYO-LLM"])

class LLMConfigRequest(BaseModel):
    provider: str = Field(..., description="e.g. openai, anthropic, gemini, groq, ollama")
    model_name: str = Field(..., description="e.g. gpt-4o, claude-3-5-sonnet, gemini-1.5-pro")
    api_key: str = Field(..., min_length=1, description="Provider API key")

class LLMConfigResponse(BaseModel):
    user_id: str
    provider: str
    model_name: str
    masked_key: str

class TestLLMRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str

@router.get("", response_model=LLMConfigResponse | None, summary="Get user's configured LLM settings")
async def get_config(
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    return await get_user_llm_config(repo, user_id)

@router.post("", response_model=LLMConfigResponse, summary="Save user's BYO-LLM configuration (encrypted at rest)")
async def set_config(
    payload: LLMConfigRequest,
    repo: NativeRepository = Depends(get_repository),
    user_id: str = Depends(get_current_user),
):
    await save_user_llm_config(
        db=repo,
        user_id=user_id,
        provider=payload.provider,
        model_name=payload.model_name,
        api_key=payload.api_key,
    )
    config = await get_user_llm_config(repo, user_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save LLM configuration",
        )
    return config

@router.post("/test", summary="Test LLM connection with provided credentials")
async def test_config(payload: TestLLMRequest):
    return await test_llm_connection(
        provider=payload.provider,
        model_name=payload.model_name,
        api_key=payload.api_key,
    )
