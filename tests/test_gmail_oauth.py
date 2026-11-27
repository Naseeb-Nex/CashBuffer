"""Tests for Gmail 3-legged OAuth endpoints, migration 007, security, and lifecycle."""

from __future__ import annotations

import datetime
from datetime import timezone
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.crypto import decrypt_key, encrypt_key
from app.infrastructure.persistence.native_repository import NativeRepository
from app.services.gmail_oauth_service import GmailOAuthService, mask_email
from main import app

@pytest.mark.asyncio
async def test_mask_email_utility():
    assert mask_email("john.doe@example.com") == "j***e@example.com"
    assert mask_email("ab@gmail.com") == "a***@gmail.com"
    assert mask_email("invalid") == "***"
    assert mask_email(None) == "***"

@pytest.mark.asyncio
async def test_migration_007_idempotent_twice(native_repo: NativeRepository):
    """Verify that migration 007 applies cleanly twice without error."""
    import os
    from app.db.native_migrations.runner import MigrationRunner

    migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
    runner = MigrationRunner(db_url=settings.DATABASE_URL, migrations_dir=migrations_dir)

    # 1. First run / verify applied
    applied = runner.run_migrations()
    assert isinstance(applied, list)

    # 2. Directly execute migration 007 SQL content again to guarantee idempotence (IF NOT EXISTS)
    migration_007_path = os.path.join(migrations_dir, "007_gmail_oauth.sql")
    with open(migration_007_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    async with native_repo.pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(sql_content)

@pytest.mark.asyncio
async def test_authorize_not_configured_returns_503(
    client: AsyncClient, auth_headers_alice: dict
):
    """GET /authorize returns 503 JSON error when Google OAuth client is unconfigured."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", ""):
        res = await client.get("/api/v1/ingress/gmail/authorize", headers=auth_headers_alice)
        assert res.status_code == 503
        data = res.json()
        assert data == {
            "code": "gmail_not_configured",
            "message": "Gmail connect is not configured on the server",
        }

@pytest.mark.asyncio
async def test_authorize_url_generation(
    client: AsyncClient,
    native_repo: NativeRepository,
    auth_headers_alice: dict,
    unique_user_alice: str,
):
    """Verify authorize URL parameters, scopes, state token JWT signature and claims."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(settings, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/ingress/gmail/callback"):

        res = await client.get("/api/v1/ingress/gmail/authorize", headers=auth_headers_alice)
        assert res.status_code == 200
        auth_url = res.json()["authorization_url"]

        parsed = urlparse(auth_url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert parsed.path == "/o/oauth2/v2/auth"

        params = parse_qs(parsed.query)
        assert params["client_id"] == ["test-client-id"]
        assert params["redirect_uri"] == ["http://localhost:8000/api/v1/ingress/gmail/callback"]
        assert params["response_type"] == ["code"]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]

        # Scope verification: least privilege
        scopes = params["scope"][0].split(" ")
        assert "https://www.googleapis.com/auth/gmail.readonly" in scopes
        assert "openid" in scopes
        assert "https://www.googleapis.com/auth/userinfo.email" in scopes

        # State token verification
        state_jwt = params["state"][0]
        service = GmailOAuthService(native_repo)
        payload = service.verify_state(state_jwt)
        assert "user_id" in payload
        assert "household_id" in payload
        assert "nonce" in payload

@pytest.mark.asyncio
async def test_callback_success_flow(
    client: AsyncClient,
    native_repo: NativeRepository,
    unique_user_alice: str,
):
    """Test callback code exchange, encryption at rest, ingress config update, and redirect."""
    user = await native_repo.get_or_create_user(unique_user_alice)
    household_id = await native_repo.get_primary_household_id(user.id)

    service = GmailOAuthService(native_repo)
    state = service.generate_state(user_id=user.id, household_id=household_id)

    raw_access_token = "mock_google_access_token_abc123"
    raw_refresh_token = "mock_google_refresh_token_xyz789"
    mock_email = "alice.finances@gmail.com"

    mock_token_resp = httpx.Response(
        status_code=200,
        json={
            "access_token": raw_access_token,
            "refresh_token": raw_refresh_token,
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/gmail.readonly openid https://www.googleapis.com/auth/userinfo.email",
        },
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )
    mock_userinfo_resp = httpx.Response(
        status_code=200,
        json={"email": mock_email, "verified_email": True},
        request=httpx.Request("GET", "https://www.googleapis.com/oauth2/v2/userinfo"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    async def mock_post(url, *args, **kwargs):
        if "oauth2.googleapis.com/token" in str(url):
            return mock_token_resp
        return httpx.Response(404, request=httpx.Request("POST", str(url)))

    async def mock_get(url, *args, **kwargs):
        if "userinfo" in str(url):
            return mock_userinfo_resp
        return httpx.Response(404, request=httpx.Request("GET", str(url)))

    mock_client.post = AsyncMock(side_effect=mock_post)
    mock_client.get = AsyncMock(side_effect=mock_get)

    with patch("app.services.gmail_oauth_service.httpx.AsyncClient", return_value=mock_client):
        res = await client.get(
            f"/api/v1/ingress/gmail/callback?code=mock_auth_code&state={state}",
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert res.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?gmail=connected"

        # Verify DB credential and encryption at rest
        cred = await native_repo.get_oauth_credential_by_household(household_id, "gmail")
        assert cred is not None
        assert cred.is_valid is True
        assert cred.account_email == mock_email
        assert cred.household_id == household_id
        assert cred.user_id == user.id

        # Ciphertext check: tokens MUST NOT be stored in plaintext
        assert cred.encrypted_access_token != raw_access_token
        assert cred.encrypted_refresh_token != raw_refresh_token
        # Fernet decryption verification
        assert decrypt_key(cred.encrypted_access_token) == raw_access_token
        assert decrypt_key(cred.encrypted_refresh_token) == raw_refresh_token

        # Ingress config verification
        cfg = await native_repo.get_ingress_config_by_household(household_id, "gmail")
        assert cfg is not None
        assert cfg["is_enabled"] is True
        assert cfg["status"] == "idle"

@pytest.mark.asyncio
async def test_callback_access_denied(client: AsyncClient):
    """Callback redirects with error when user denies consent."""
    res = await client.get(
        "/api/v1/ingress/gmail/callback?error=access_denied&error_description=User+denied",
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?error=access_denied"

@pytest.mark.asyncio
async def test_callback_invalid_and_expired_state(
    client: AsyncClient,
    native_repo: NativeRepository,
    unique_user_alice: str,
):
    """Callback rejects tampered and expired state tokens."""
    # 1. Tampered state
    res1 = await client.get(
        "/api/v1/ingress/gmail/callback?code=some_code&state=bad.tampered.token",
        follow_redirects=False,
    )
    assert res1.status_code == 302
    assert res1.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?error=invalid_state"

    # 2. Expired state
    service = GmailOAuthService(native_repo)
    secret = service.get_state_secret()
    expired_payload = {
        "sub": "user_id_123",
        "user_id": "user_id_123",
        "household_id": "household_id_123",
        "nonce": "expired_nonce",
        "exp": datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=5),
    }
    expired_state = jwt.encode(expired_payload, secret, algorithm="HS256")

    res2 = await client.get(
        f"/api/v1/ingress/gmail/callback?code=some_code&state={expired_state}",
        follow_redirects=False,
    )
    assert res2.status_code == 302
    assert res2.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?error=invalid_state"

@pytest.mark.asyncio
async def test_callback_missing_refresh_token_fallback_and_error(
    client: AsyncClient,
    native_repo: NativeRepository,
    unique_user_alice: str,
):
    """
    When Google returns no refresh_token:
    1. If no prior refresh_token exists -> redirect error=no_refresh_token
    2. If prior refresh_token exists -> reuse stored refresh token successfully
    """
    user = await native_repo.get_or_create_user(unique_user_alice)
    household_id = await native_repo.get_primary_household_id(user.id)
    service = GmailOAuthService(native_repo)

    mock_token_no_refresh = httpx.Response(
        status_code=200,
        json={
            "access_token": "mock_new_access_token",
            "expires_in": 3600,
        },
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )
    mock_userinfo = httpx.Response(
        status_code=200,
        json={"email": "alice@gmail.com"},
        request=httpx.Request("GET", "https://www.googleapis.com/oauth2/v2/userinfo"),
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_token_no_refresh)
    mock_client.get = AsyncMock(return_value=mock_userinfo)

    with patch("app.services.gmail_oauth_service.httpx.AsyncClient", return_value=mock_client):
        # Case 1: No stored refresh token exists
        state1 = service.generate_state(user_id=user.id, household_id=household_id)
        res1 = await client.get(
            f"/api/v1/ingress/gmail/callback?code=auth_code_1&state={state1}",
            follow_redirects=False,
        )
        assert res1.status_code == 302
        assert res1.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?error=no_refresh_token"

        # Seed a prior credential with stored encrypted refresh token
        prior_refresh = "stored_legacy_refresh_token_999"
        await native_repo.upsert_oauth_credential(
            user_id=user.id,
            household_id=household_id,
            source="gmail",
            encrypted_access_token=encrypt_key("old_access"),
            encrypted_refresh_token=encrypt_key(prior_refresh),
            expires_at=datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
            account_email="alice@gmail.com",
            is_valid=True,
        )

        # Case 2: Fallback to existing stored refresh token succeeds
        state2 = service.generate_state(user_id=user.id, household_id=household_id)
        res2 = await client.get(
            f"/api/v1/ingress/gmail/callback?code=auth_code_2&state={state2}",
            follow_redirects=False,
        )
        assert res2.status_code == 302
        assert res2.headers["location"] == f"{settings.WEB_BASE_URL.rstrip('/')}/settings?gmail=connected"

        # Verify stored refresh token was preserved
        cred = await native_repo.get_oauth_credential_by_household(household_id, "gmail")
        assert cred is not None
        assert decrypt_key(cred.encrypted_refresh_token) == prior_refresh
        assert decrypt_key(cred.encrypted_access_token) == "mock_new_access_token"

@pytest.mark.asyncio
async def test_status_endpoint_states(
    client: AsyncClient,
    native_repo: NativeRepository,
    auth_headers_alice: dict,
    unique_user_alice: str,
):
    """Verify status transitions: not_connected -> connected -> needs_reconnect."""
    user = await native_repo.get_or_create_user(unique_user_alice)
    household_id = await native_repo.get_primary_household_id(user.id)

    # 1. Initially not_connected
    res1 = await client.get("/api/v1/ingress/gmail/status", headers=auth_headers_alice)
    assert res1.status_code == 200
    assert res1.json() == {
        "connected": False,
        "status": "not_connected",
        "account_email": None,
        "last_synced_at": None,
        "interval_minutes": 60,
        "is_enabled": False,
    }

    # 2. Connected
    await native_repo.upsert_oauth_credential(
        user_id=user.id,
        household_id=household_id,
        source="gmail",
        encrypted_access_token=encrypt_key("active_token"),
        encrypted_refresh_token=encrypt_key("active_refresh"),
        expires_at=datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
        account_email="status.test@gmail.com",
        is_valid=True,
    )
    await native_repo.ensure_ingress_config_enabled(household_id, user.id, "gmail")

    res2 = await client.get("/api/v1/ingress/gmail/status", headers=auth_headers_alice)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["connected"] is True
    assert data2["status"] == "connected"
    assert data2["account_email"] == "status.test@gmail.com"
    assert data2["is_enabled"] is True

    # 3. Invalidated -> needs_reconnect
    async with native_repo.pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE oauth_credentials SET is_valid = FALSE WHERE household_id = %s AND source = 'gmail';",
                    (household_id,),
                )

    res3 = await client.get("/api/v1/ingress/gmail/status", headers=auth_headers_alice)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["connected"] is False
    assert data3["status"] == "needs_reconnect"
    assert data3["account_email"] == "status.test@gmail.com"

@pytest.mark.asyncio
async def test_disconnect_owner_and_non_owner(
    client: AsyncClient,
    native_repo: NativeRepository,
    auth_headers_alice: dict,
    unique_user_alice: str,
    auth_headers_bob: dict,
    unique_user_bob: str,
):
    """
    Disconnect endpoint permissions:
    - Non-owner (member): 403 Forbidden
    - Owner: 200 OK, best-effort revoke, is_valid=False, ingress_config disabled
    """
    alice = await native_repo.get_or_create_user(unique_user_alice)
    household_id = await native_repo.get_primary_household_id(alice.id)

    # Bob joins Alice's household as a standard 'member' (clear any auto-created household)
    bob = await native_repo.get_or_create_user(unique_user_bob)
    async with native_repo.pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM household_members WHERE user_id = %s;", (bob.id,))
                await cur.execute(
                    """
                    INSERT INTO household_members (household_id, user_id, role, joined_at)
                    VALUES (%s, %s, 'member', CURRENT_TIMESTAMP);
                    """,
                    (household_id, bob.id),
                )

    # Set up active credential for household
    await native_repo.upsert_oauth_credential(
        user_id=alice.id,
        household_id=household_id,
        source="gmail",
        encrypted_access_token=encrypt_key("token_to_revoke"),
        encrypted_refresh_token=encrypt_key("refresh_to_revoke"),
        expires_at=datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
        account_email="alice.owner@gmail.com",
        is_valid=True,
    )
    await native_repo.ensure_ingress_config_enabled(household_id, alice.id, "gmail")

    # 1. Bob (non-owner) attempts disconnect -> 403 Forbidden
    res_bob = await client.post("/api/v1/ingress/gmail/disconnect", headers=auth_headers_bob)
    assert res_bob.status_code == 403
    assert "owner" in res_bob.json()["detail"].lower()

    # 2. Alice (owner) attempts disconnect -> 200 OK
    mock_revoke_client = AsyncMock()
    mock_revoke_client.__aenter__.return_value = mock_revoke_client
    mock_revoke_client.__aexit__.return_value = None
    mock_revoke_client.post = AsyncMock(return_value=httpx.Response(200, request=httpx.Request("POST", "https://oauth2.googleapis.com/revoke")))

    with patch("app.services.gmail_oauth_service.httpx.AsyncClient", return_value=mock_revoke_client):
        res_alice = await client.post("/api/v1/ingress/gmail/disconnect", headers=auth_headers_alice)
        assert res_alice.status_code == 200
        assert res_alice.json() == {
            "success": True,
            "message": "Gmail account disconnected",
        }

    # Verify DB state
    cred = await native_repo.get_oauth_credential_by_household(household_id, "gmail")
    assert cred is not None
    assert cred.is_valid is False

    cfg = await native_repo.get_ingress_config_by_household(household_id, "gmail")
    assert cfg is not None
    assert cfg["is_enabled"] is False
    assert cfg["status"] == "disconnected"
