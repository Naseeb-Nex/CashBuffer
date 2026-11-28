"""Gmail OAuth 2.0 API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.core.config import settings
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.gmail_oauth_service import GmailOAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail Ingress"])

class GmailStatusResponse(BaseModel):
    connected: bool
    status: str
    account_email: str | None = None
    last_synced_at: str | None = None
    interval_minutes: int = 60
    is_enabled: bool = False

class GmailAuthorizeResponse(BaseModel):
    authorization_url: str

class GmailDisconnectResponse(BaseModel):
    success: bool
    message: str

def get_gmail_service(repo: NativeRepository = Depends(get_repository)) -> GmailOAuthService:
    return GmailOAuthService(repo=repo)

@router.get(
    "/status",
    response_model=GmailStatusResponse,
    summary="Get Gmail connection status for household",
)
async def get_gmail_status(
    idp_user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> Any:
    user = await repo.get_or_create_user(idp_user_id)
    household_id = await repo.get_primary_household_id(user.id)
    return await service.get_status(household_id=household_id)

@router.get(
    "/authorize",
    response_model=GmailAuthorizeResponse,
    summary="Initiate Gmail 3-legged OAuth consent flow",
)
async def authorize_gmail(
    idp_user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> Any:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "gmail_not_configured",
                "message": "Gmail connect is not configured on the server",
            },
        )

    user = await repo.get_or_create_user(idp_user_id)
    household_id = await repo.get_primary_household_id(user.id)
    auth_url = await service.get_authorize_url(user_id=user.id, household_id=household_id)
    return {"authorization_url": auth_url}

@router.get(
    "/callback",
    summary="OAuth callback redirect from Google",
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
async def gmail_oauth_callback(
    code: str | None = Query(None, description="Google authorization code"),
    state: str | None = Query(None, description="Signed state token"),
    error: str | None = Query(None, description="OAuth error code from Google"),
    error_description: str | None = Query(None, description="OAuth error description"),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> Any:
    redirect_target = await service.handle_callback(code=code, state=state, error=error)
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)

@router.post(
    "/disconnect",
    response_model=GmailDisconnectResponse,
    summary="Disconnect Gmail account (Owner only)",
)
async def disconnect_gmail(
    idp_user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
    service: GmailOAuthService = Depends(get_gmail_service),
) -> Any:
    user = await repo.get_or_create_user(idp_user_id)
    household_id = await repo.get_primary_household_id(user.id)
    await service.disconnect(user_id=user.id, household_id=household_id)
    return {"success": True, "message": "Gmail account disconnected"}
