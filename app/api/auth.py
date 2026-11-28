from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.infrastructure.persistence.deps import get_repository
from app.infrastructure.persistence.native_repository import NativeRepository

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)

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
    Returns the external Subject / identity string (idp_user_id).
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

    if settings.KINDE_DOMAIN:
        if not settings.KINDE_AUDIENCE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="KINDE_AUDIENCE is not configured on the server",
            )
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

            clean_domain = settings.KINDE_DOMAIN.rstrip("/")
            expected_issuers = [clean_domain, f"{clean_domain}/"]

            payload = jwt.decode(
                token,
                key=jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
                algorithms=["RS256"],
                audience=settings.KINDE_AUDIENCE,
                issuer=expected_issuers,
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_signature": True,
                },
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

    # Self-hosted / local mode: Verify via LOCAL_JWT_SECRET if configured
    if settings.LOCAL_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                key=settings.LOCAL_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            user_id = payload.get("sub") or payload.get("user_id")
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

    # Fallback for dev / unconfigured local environments
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id:
            return str(user_id)
    except Exception:
        pass

    return str(token)

@router.get("/me", summary="Get current user profile")
async def get_me(
    user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
):
    user = await repo.get_or_create_user(idp_user_id=user_id)
    return {
        "id": user.id,
        "idp_user_id": user.idp_user_id,
        "email": user.email,
        "telegram_chat_id": user.telegram_chat_id,
        "created_at": user.created_at,
    }

@router.post("/link-telegram", summary="Link telegram chat ID to user")
async def link_telegram(
    telegram_chat_id: str,
    user_id: str = Depends(get_current_user),
    repo: NativeRepository = Depends(get_repository),
):
    user = await repo.get_or_create_user(idp_user_id=user_id)
    await repo.set_telegram_chat_id(user_id=user.id, chat_id=telegram_chat_id)
    return {"status": "linked", "telegram_chat_id": telegram_chat_id}
