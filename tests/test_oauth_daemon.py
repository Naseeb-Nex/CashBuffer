import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.db.models import OAuthCredential
from app.services.oauth_daemon import refresh_tokens
from app.core.crypto import encrypt_key, decrypt_key
from sqlalchemy import select


@pytest.mark.asyncio
async def test_refresh_tokens_success(db_session, unique_user_alice):
    # Setup mock data
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    cred = OAuthCredential(
        user_id=unique_user_alice,
        source="gmail",
        encrypted_access_token=encrypt_key("old_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=expired_time,
        is_valid=True
    )
    db_session.add(cred)
    await db_session.commit()

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh_token = "valid_refresh_token"
        mock_instance.token = "new_access_token"
        mock_instance.expiry = now + timedelta(hours=1)

        MockCreds.return_value = mock_instance

        await refresh_tokens(db_session)

        # Verify the mock was called correctly
        mock_instance.refresh.assert_called_once()

    # Verify DB was updated
    await db_session.refresh(cred)
    assert decrypt_key(cred.encrypted_access_token) == "new_access_token"
    assert cred.expires_at.replace(tzinfo=timezone.utc) > now

@pytest.mark.asyncio
async def test_refresh_tokens_error_handling(db_session, unique_user_alice, caplog):
    # Setup mock data
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    cred = OAuthCredential(
        user_id=unique_user_alice,
        source="gmail",
        encrypted_access_token=encrypt_key("old_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=expired_time,
        is_valid=True
    )
    db_session.add(cred)
    await db_session.commit()

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh_token = "valid_refresh_token"
        mock_instance.refresh.side_effect = Exception("Auth Error")

        MockCreds.return_value = mock_instance

        await refresh_tokens(db_session)

        # Verify the mock was called
        mock_instance.refresh.assert_called_once()

    # Verify DB was NOT updated for token but is_valid was set to False
    await db_session.refresh(cred)
    assert decrypt_key(cred.encrypted_access_token) == "old_access_token"
    assert cred.is_valid is False
    assert "Failed to refresh OAuth token" in caplog.text

@pytest.mark.asyncio
async def test_refresh_tokens_skips_valid(db_session, unique_user_alice):
    # Setup mock data
    now = datetime.now(timezone.utc)
    valid_time = now + timedelta(hours=1)

    cred = OAuthCredential(
        user_id=unique_user_alice,
        source="gmail",
        encrypted_access_token=encrypt_key("valid_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=valid_time,
        is_valid=True
    )
    db_session.add(cred)
    await db_session.commit()

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        await refresh_tokens(db_session)
        # Should not be called because it's not expiring soon
        MockCreds.assert_not_called()
