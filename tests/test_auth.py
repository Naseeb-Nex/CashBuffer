import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.auth import get_current_user
from app.core.config import settings

# Generate a test RSA key pair for simulating Kinde JWKS
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(_public_key, as_dict=True)
_jwk["kid"] = "test-kid-1"
_jwk["use"] = "sig"


def _create_kinde_token(
    sub: str | None = "user_kinde_123",
    aud: str | None = "https://api.cashbuffer.local",
    iss: str | None = "https://test.kinde.com",
    expired: bool = False,
    kid: str = "test-kid-1",
) -> str:
    now = int(time.time())
    payload = {
        "exp": now - 3600 if expired else now + 3600,
        "iat": now - 60,
    }
    if sub is not None:
        payload["sub"] = sub
    if aud is not None:
        payload["aud"] = aud
    if iss is not None:
        payload["iss"] = iss

    headers = {"kid": kid, "alg": "RS256"}
    return jwt.encode(payload, _private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def mock_jwks():
    with patch("app.api.auth.get_jwks", new_callable=AsyncMock) as m:
        m.return_value = {"keys": [_jwk]}
        yield m


@pytest.mark.asyncio
async def test_kinde_auth_valid_token(mock_jwks):
    token = _create_kinde_token()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        sub = await get_current_user(credentials)
        assert sub == "user_kinde_123"


@pytest.mark.asyncio
async def test_kinde_auth_wrong_aud(mock_jwks):
    token = _create_kinde_token(aud="https://wrong-api.local")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token verification failed" in exc_info.value.detail
        assert "Audience doesn't match" in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_missing_aud(mock_jwks):
    token = _create_kinde_token(aud=None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token verification failed" in exc_info.value.detail
        assert 'Token is missing the "aud" claim' in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_expired(mock_jwks):
    token = _create_kinde_token(expired=True)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Signature has expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_wrong_issuer(mock_jwks):
    token = _create_kinde_token(iss="https://attacker-idp.com")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Invalid issuer" in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_missing_sub(mock_jwks):
    token = _create_kinde_token(sub=None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token missing subject (sub) claim" in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_missing_configured_audience(mock_jwks):
    token = _create_kinde_token()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", ""
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 500
        assert "KINDE_AUDIENCE is not configured" in exc_info.value.detail


@pytest.mark.asyncio
async def test_local_jwt_valid():
    secret = "test-secret-key-that-is-at-least-32-chars-long"
    payload = {"sub": "local-user-uuid", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, secret, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", ""), patch.object(
        settings, "LOCAL_JWT_SECRET", secret
    ):
        sub = await get_current_user(credentials)
        assert sub == "local-user-uuid"


@pytest.mark.asyncio
async def test_local_jwt_expired():
    secret = "test-secret-key-that-is-at-least-32-chars-long"
    payload = {"sub": "local-user-uuid", "exp": int(time.time()) - 3600}
    token = jwt.encode(payload, secret, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", ""), patch.object(
        settings, "LOCAL_JWT_SECRET", secret
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token verification failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_local_jwt_wrong_secret():
    secret = "test-secret-key-that-is-at-least-32-chars-long"
    wrong_secret = "different-secret-key-at-least-32-characters"
    payload = {"sub": "local-user-uuid", "exp": int(time.time()) + 3600}
    token = jwt.encode(payload, wrong_secret, algorithm="HS256")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", ""), patch.object(
        settings, "LOCAL_JWT_SECRET", secret
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token verification failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None)
    assert exc_info.value.status_code == 401
    assert "Missing authorization bearer token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_empty_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)
    assert exc_info.value.status_code == 401
    assert "Empty bearer token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_kinde_auth_wrong_alg(mock_jwks):
    # Test algorithm confusion: signing with HS256 instead of RS256
    secret = "a" * 32
    token = jwt.encode(
        {
            "sub": "user_kinde_123",
            "aud": "https://api.cashbuffer.local",
            "iss": "https://test.kinde.com",
            "exp": int(time.time()) + 3600,
        },
        secret,
        algorithm="HS256",
        headers={"kid": "test-kid-1"},
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with patch.object(settings, "KINDE_DOMAIN", "https://test.kinde.com"), patch.object(
        settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401
        assert "Token verification failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_jwks_rotation_cache_miss_refetches():
    # Simulate first JWKS having only kid-old
    old_jwk = dict(_jwk)
    old_jwk["kid"] = "kid-old"

    # Second JWKS having both kid-old and kid-new
    new_jwk = dict(_jwk)
    new_jwk["kid"] = "kid-new"

    mock_client = AsyncMock()
    mock_resp_1 = AsyncMock(status_code=200, json=lambda: {"keys": [old_jwk]})
    mock_resp_2 = AsyncMock(status_code=200, json=lambda: {"keys": [old_jwk, new_jwk]})
    mock_client.get.side_effect = [mock_resp_1, mock_resp_2]

    import app.api.auth as auth_mod
    auth_mod._JWKS = None
    auth_mod._JWKS_LAST_FETCH_TIME = 0.0

    with patch("httpx.AsyncClient") as mock_client_cls, patch.object(
        settings, "KINDE_DOMAIN", "https://test.kinde.com"
    ), patch.object(settings, "KINDE_AUDIENCE", "https://api.cashbuffer.local"), patch(
        "app.api.auth._JWKS_MIN_REFETCH_INTERVAL", 0.0
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        token = _create_kinde_token(kid="kid-new")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        sub = await get_current_user(credentials)
        assert sub == "user_kinde_123"
        # Should have fetched twice: initial fetch and rotated key refetch
        assert mock_client.get.call_count == 2

