from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.db.models import OAuthCredential
from app.services.oauth_daemon import refresh_credentials


@pytest.fixture
async def expired_credential(db_session):
    cred = OAuthCredential(
        user_id="test_user",
        provider="google",
        access_token="old_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    return cred


@pytest.fixture
async def valid_credential(db_session):
    cred = OAuthCredential(
        user_id="test_user",
        provider="google",
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    return cred


@pytest.mark.asyncio
@patch("app.services.oauth_daemon.AsyncSessionLocal")
@patch("app.services.oauth_daemon.Credentials")
async def test_refresh_credentials_success(mock_credentials, mock_session_local, expired_credential, db_session):
    # Setup mock to update credentials when refreshed
    mock_cred_instance = MagicMock()
    mock_cred_instance.token = "new_access_token"
    mock_cred_instance.refresh_token = "new_refresh_token"
    mock_cred_instance.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_credentials.return_value = mock_cred_instance

    # We yield the db_session as the session
    mock_session_local.return_value.__aenter__.return_value = db_session

    with (
        patch.object(settings, "GOOGLE_CLIENT_ID", "test_client_id"),
        patch.object(settings, "GOOGLE_CLIENT_SECRET", "test_client_secret"),
    ):
        await refresh_credentials()

    # Validation
    await db_session.refresh(expired_credential)
    assert expired_credential.access_token == "new_access_token"
    assert expired_credential.refresh_token == "new_refresh_token"
    assert expired_credential.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


@pytest.mark.asyncio
@patch("app.services.oauth_daemon.AsyncSessionLocal")
@patch("app.services.oauth_daemon.Credentials")
async def test_refresh_credentials_ignores_valid(mock_credentials, mock_session_local, valid_credential, db_session):
    mock_session_local.return_value.__aenter__.return_value = db_session

    await refresh_credentials()

    assert not mock_credentials.called


@pytest.mark.asyncio
@patch("app.services.oauth_daemon.AsyncSessionLocal")
@patch("app.services.oauth_daemon.Credentials")
async def test_refresh_credentials_error_handling(mock_credentials, mock_session_local, expired_credential, db_session):
    mock_cred_instance = MagicMock()
    mock_cred_instance.refresh.side_effect = Exception("Auth failed")
    mock_credentials.return_value = mock_cred_instance

    mock_session_local.return_value.__aenter__.return_value = db_session

    with (
        patch.object(settings, "GOOGLE_CLIENT_ID", "test_client_id"),
        patch.object(settings, "GOOGLE_CLIENT_SECRET", "test_client_secret"),
    ):
        await refresh_credentials()

    # Ensure it didn't change and didn't crash
    await db_session.refresh(expired_credential)
    assert expired_credential.access_token == "old_access_token"
