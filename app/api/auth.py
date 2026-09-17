from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)

# We cache the JWKS in memory
_JWKS: dict[str, Any] | None = None


async def get_jwks() -> dict[str, Any]:
    global _JWKS
    if _JWKS is None:
        if not settings.KINDE_DOMAIN:
            return {"keys": []}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.KINDE_DOMAIN}/.well-known/jwks.json")
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not fetch Kinde JWKS",
                )
            _JWKS = resp.json()
    return _JWKS


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Dependency that validates the JWT Bearer Token from Kinde or dev fallback.
    Returns the Subject (user_id).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. If Kinde is configured, verify signature against Kinde JWKS
    if settings.KINDE_DOMAIN:
        try:
            jwks = await get_jwks()
            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key.get("kid") == unverified_header.get("kid"):
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key.get("use", "sig"),
                        "n": key["n"],
                        "e": key["e"],
                    }
                    break
            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key in JWKS",
                )

            payload = jwt.decode(
                token,
                key=jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
                algorithms=["RS256"],
                audience=settings.KINDE_CLIENT_ID or None,
                options={"verify_aud": bool(settings.KINDE_CLIENT_ID)},
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject (sub) claim",
                )
            return str(user_id)
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {e!s}",
            )

    # 2. In dev/test mode (KINDE_DOMAIN not configured), decode JWT payload or accept identifier
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id:
            return str(user_id)
    except Exception:
        pass

    # Direct user token string fallback for testing (e.g. "user_test_123")
    return str(token)


@router.get("/me", summary="Get current user profile")
async def get_me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@cashbuffer.local")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "telegram_chat_id": user.telegram_chat_id,
        "created_at": user.created_at,
    }


@router.post("/link-telegram", summary="Link telegram chat ID to user")
async def link_telegram(
    telegram_chat_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@cashbuffer.local", telegram_chat_id=telegram_chat_id)
        db.add(user)
    else:
        user.telegram_chat_id = telegram_chat_id
    await db.commit()
    return {"status": "success", "user_id": user_id, "telegram_chat_id": telegram_chat_id}
