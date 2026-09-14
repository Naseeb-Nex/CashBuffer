from typing import Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

router = APIRouter()
security = HTTPBearer()

# We will cache the JWKS in memory so we don't hit the Kinde API on every request.
_JWKS = None

async def get_jwks() -> dict[str, Any]:
    global _JWKS
    if _JWKS is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.KINDE_DOMAIN}/.well-known/jwks.json")
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Could not fetch Kinde JWKS")
            _JWKS = resp.json()
    return _JWKS

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency that validates the JWT Bearer Token from Kinde.
    Returns the Kinde Subject (user_id).
    Next.js frontend passes this token via: `Authorization: Bearer <token>`
    """
    token = credentials.credentials
    try:
        # 1. Fetch Kinde's Public Keys
        jwks = await get_jwks()
        
        # 2. Extract the unverified header to find the kid (key ID)
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
                
        if not rsa_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to find appropriate key")
            
        # 3. Cryptographically verify the token
        payload = jwt.decode(
            token,
            key=jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key),
            algorithms=["RS256"],
            audience=f"{settings.KINDE_DOMAIN}/api"
        )
        
        # 4. Extract standard JWT Subject
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
            
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me")
async def verify_me(user_id: str = Depends(get_current_user)):
    """Simple test route to prove decoupled JWT authentication works."""
    return {"status": "authenticated", "user_id": user_id}
