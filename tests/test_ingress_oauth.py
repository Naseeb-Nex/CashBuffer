"""Tests for per-household Gmail OAuth token loading, refresh, and error handling in Ingress microservice."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
import httplib2

from app.core.crypto import encrypt_key
from apps.ingress.src.application.sync_service import IngressSyncService
from apps.ingress.src.domain.models import IngressJob, OAuthCredential
from apps.ingress.src.infrastructure.gmail.client import GmailClient, mask_email
from apps.ingress.src.infrastructure.persistence.ingress_repository import (
    NativeIngressRepository,
)


def test_mask_email():
    assert mask_email("user@gmail.com") == "u**r@gmail.com"
    assert mask_email("me@domain.com") == "m*@domain.com"
    assert mask_email("a@b.com") == "*@b.com"
    assert mask_email("") == "***"
    assert mask_email(None) == "***"


@pytest.mark.asyncio
async def test_gmail_client_for_household_db_token():
    """Verify loading and building Credentials from DB encrypted OAuth credential."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    uid = uuid.uuid4()

    enc_access = encrypt_key("db-access-token-123")
    enc_refresh = encrypt_key("db-refresh-token-456")

    db_cred = OAuthCredential(
        id=42,
        user_id=uid,
        household_id=hid,
        source="gmail",
        encrypted_access_token=enc_access,
        encrypted_refresh_token=enc_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_valid=True,
        account_email="masked_user@gmail.com",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    mock_repo.get_oauth_credential.return_value = db_cred

    client = await GmailClient.for_household(household_id=hid, repo=mock_repo)
    assert client is not None
    assert client.household_id == hid
    assert client.credential_id == 42
    assert client._credentials is not None
    assert client._credentials.token == "db-access-token-123"
    assert client._credentials.refresh_token == "db-refresh-token-456"
    mock_repo.get_oauth_credential.assert_awaited_once_with(household_id=hid, source="gmail")


@pytest.mark.asyncio
async def test_gmail_client_for_household_file_fallback(tmp_path):
    """Verify fallback to GMAIL_TOKEN_PATH when DB has no credential."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    mock_repo.get_oauth_credential.return_value = None

    token_file = tmp_path / "token.json"
    token_file.write_text(
        '{"token": "file-token", "refresh_token": "file-refresh", "client_id": "cid", "client_secret": "csec", "scopes": []}'
    )

    with patch.dict("os.environ", {"GMAIL_TOKEN_PATH": str(token_file)}):
        client = await GmailClient.for_household(household_id=hid, repo=mock_repo)
        assert client is not None
        assert client.household_id == hid
        assert client.credential_id is None
        assert client._credentials is not None
        assert client._credentials.token == "file-token"


@pytest.mark.asyncio
async def test_gmail_client_for_household_neither_present_skips():
    """Verify returning None when neither DB nor file credential exists."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    mock_repo.get_oauth_credential.return_value = None

    with patch.dict("os.environ", {"GMAIL_TOKEN_PATH": "/nonexistent/token.json"}):
        with patch("os.path.exists", return_value=False):
            client = await GmailClient.for_household(household_id=hid, repo=mock_repo)
            assert client is None


@pytest.mark.asyncio
async def test_expired_token_refresh_persists_ciphertext():
    """Verify expired token refresh calls creds.refresh and writes encrypted ciphertext to repo."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()

    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.token = "new-refreshed-access-token"
    mock_creds.refresh_token = "db-refresh-token"
    mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {"messages": []}

    client = GmailClient(
        service=mock_service,
        credentials=mock_creds,
        household_id=hid,
        credential_id=99,
        repo=mock_repo,
    )

    messages = await client.fetch_alert_messages()
    assert messages == []
    mock_creds.refresh.assert_called_once()
    mock_repo.update_oauth_credential.assert_awaited_once()

    call_args = mock_repo.update_oauth_credential.call_args[1]
    assert call_args["credential_id"] == 99
    # Verify ciphertext is not plaintext
    assert call_args["encrypted_access_token"] != "new-refreshed-access-token"
    from app.core.crypto import decrypt_key
    assert decrypt_key(call_args["encrypted_access_token"]) == "new-refreshed-access-token"


@pytest.mark.asyncio
async def test_sync_service_skips_when_no_credentials():
    """Verify sync_service gracefully skips household when no credentials exist without crashing."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    uid = uuid.uuid4()
    job = IngressJob(
        id=uuid.uuid4(),
        household_id=hid,
        user_id=uid,
        provider="gmail",
        interval_minutes=60,
        next_run_at=datetime.now(timezone.utc),
        status="idle",
    )

    mock_repo.get_oauth_credential.return_value = None
    with patch("apps.ingress.src.infrastructure.gmail.client.os.path.exists", return_value=False):
        sync = IngressSyncService(repository=mock_repo, email_client=None, parser=None)
        res = await sync.execute_job(job)
        assert res["success"] is False
        assert res["skipped"] is True
        assert res["reason"] == "no_credentials"
        # Repository mark_job_status not failed
        mock_repo.mark_job_status.assert_not_called()


@pytest.mark.asyncio
async def test_sync_service_on_refresh_error_transitions_to_needs_reconnect():
    """Verify RefreshError marks credential invalid and status to needs_reconnect."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    uid = uuid.uuid4()
    job = IngressJob(
        id=uuid.uuid4(),
        household_id=hid,
        user_id=uid,
        provider="gmail",
        interval_minutes=60,
        next_run_at=datetime.now(timezone.utc),
        status="idle",
    )

    mock_client = AsyncMock()
    mock_client.fetch_alert_messages.side_effect = RefreshError("invalid_grant: Token has been revoked.")

    sync = IngressSyncService(repository=mock_repo, email_client=mock_client, parser=None)
    res = await sync.execute_job(job)

    assert res["success"] is False
    assert res["status"] == "needs_reconnect"
    assert "token" not in res["error"].lower() or "revoked" in res["error"].lower()

    # Credential invalidated
    mock_repo.mark_oauth_credential_invalid.assert_awaited_once_with(
        household_id=hid,
        source="gmail",
    )
    # Config marked needs_reconnect
    mock_repo.mark_job_status.assert_awaited_once_with(
        job_id=job.id,
        status="needs_reconnect",
        interval_minutes=60,
        error="Gmail access revoked or expired. Reconnection required.",
    )


@pytest.mark.asyncio
async def test_sync_service_on_http_401_transitions_to_needs_reconnect():
    """Verify HTTP 401 marks credential invalid and status to needs_reconnect."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    uid = uuid.uuid4()
    job = IngressJob(
        id=uuid.uuid4(),
        household_id=hid,
        user_id=uid,
        provider="gmail",
        interval_minutes=60,
        next_run_at=datetime.now(timezone.utc),
        status="idle",
    )

    mock_client = AsyncMock()
    resp = httplib2.Response({"status": 401})
    mock_client.fetch_alert_messages.side_effect = HttpError(resp, b"Unauthorized")

    sync = IngressSyncService(repository=mock_repo, email_client=mock_client, parser=None)
    res = await sync.execute_job(job)

    assert res["success"] is False
    assert res["status"] == "needs_reconnect"
    mock_repo.mark_oauth_credential_invalid.assert_awaited_once_with(
        household_id=hid,
        source="gmail",
    )
    mock_repo.mark_job_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_service_skips_needs_reconnect_status():
    """Verify a job in needs_reconnect state is skipped and not retried."""
    mock_repo = AsyncMock()
    hid = uuid.uuid4()
    job = IngressJob(
        id=uuid.uuid4(),
        household_id=hid,
        user_id=uuid.uuid4(),
        provider="gmail",
        interval_minutes=60,
        next_run_at=datetime.now(timezone.utc),
        status="needs_reconnect",
    )

    sync = IngressSyncService(repository=mock_repo, email_client=None, parser=None)
    res = await sync.execute_job(job)
    assert res["success"] is False
    assert res["skipped"] is True
    assert res["reason"] == "needs_reconnect"


@pytest.mark.asyncio
async def test_multi_household_token_isolation():
    """Verify Household A's credentials are never used for Household B."""
    mock_repo = AsyncMock()
    hid_a = uuid.uuid4()
    hid_b = uuid.uuid4()

    cred_a = OAuthCredential(
        id=1,
        user_id=uuid.uuid4(),
        household_id=hid_a,
        source="gmail",
        encrypted_access_token=encrypt_key("token-household-A"),
        encrypted_refresh_token=encrypt_key("refresh-A"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_valid=True,
    )
    cred_b = OAuthCredential(
        id=2,
        user_id=uuid.uuid4(),
        household_id=hid_b,
        source="gmail",
        encrypted_access_token=encrypt_key("token-household-B"),
        encrypted_refresh_token=encrypt_key("refresh-B"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_valid=True,
    )

    async def get_cred(household_id, source="gmail"):
        if household_id == hid_a:
            return cred_a
        elif household_id == hid_b:
            return cred_b
        return None

    mock_repo.get_oauth_credential.side_effect = get_cred

    client_a = await GmailClient.for_household(household_id=hid_a, repo=mock_repo)
    client_b = await GmailClient.for_household(household_id=hid_b, repo=mock_repo)

    assert client_a.household_id == hid_a
    assert client_b.household_id == hid_b
    assert client_a.credential_id == 1
    assert client_b.credential_id == 2
    assert client_a._credentials.token == "token-household-A"
    assert client_b._credentials.token == "token-household-B"
    assert client_a._credentials.token != client_b._credentials.token


@pytest.mark.asyncio
async def test_native_ingress_repository_oauth_methods():
    """Verify NativeIngressRepository methods for oauth_credentials and ingress_configs."""
    mock_cursor = AsyncMock()
    mock_conn = MagicMock()
    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor_ctx

    mock_pool = MagicMock()
    mock_pool.connection.return_value.__aenter__.return_value = mock_conn

    repo = NativeIngressRepository(mock_pool)
    hid = uuid.uuid4()
    uid = uuid.uuid4()

    # 1. get_oauth_credential
    mock_cursor.fetchone.return_value = {
        "id": 10,
        "user_id": str(uid),
        "household_id": str(hid),
        "source": "gmail",
        "encrypted_access_token": "enc_access",
        "encrypted_refresh_token": "enc_refresh",
        "expires_at": datetime.now(timezone.utc),
        "is_valid": True,
        "account_email": "test@gmail.com",
        "scopes": ["gmail.readonly"],
        "created_at": None,
        "updated_at": None,
    }
    cred = await repo.get_oauth_credential(household_id=hid, source="gmail")
    assert cred is not None
    assert cred.id == 10
    assert cred.household_id == hid
    assert "SELECT id, user_id, household_id" in mock_cursor.execute.call_args[0][0]

    # 2. update_oauth_credential
    await repo.update_oauth_credential(
        credential_id=10,
        encrypted_access_token="new_enc_access",
        expires_at=datetime.now(timezone.utc),
    )
    assert "UPDATE oauth_credentials" in mock_cursor.execute.call_args[0][0]

    # 3. mark_oauth_credential_invalid
    await repo.mark_oauth_credential_invalid(household_id=hid, source="gmail")
    assert "is_valid = FALSE" in mock_cursor.execute.call_args[0][0]

    # 4. update_ingress_config_status
    await repo.update_ingress_config_status(
        household_id=hid,
        status="needs_reconnect",
        error="Reconnection required",
    )
    assert "UPDATE ingress_configs" in mock_cursor.execute.call_args[0][0]
