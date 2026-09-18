from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
<<<<<<< HEAD

import pytest

from app.core.crypto import decrypt_key, encrypt_key
from app.db.models import OAuthCredential
from app.services.oauth_daemon import refresh_tokens
=======

import pytest

from app.core.crypto import decrypt_key, encrypt_key
from app.db.models import OAuthCredential, User
from app.services.oauth_daemon import refresh_google_token
>>>>>>> 9b1d119 (no-mistakes(document): Updated documentation and lint for OAuth refresh daemon)


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
        is_valid=True,
    )
    db_session.add(cred)
    await db_session.commit()

<<<<<<< HEAD
    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh_token = "valid_refresh_token"
        mock_instance.token = "new_access_token"
        mock_instance.expiry = now + timedelta(hours=1)

        MockCreds.return_value = mock_instance
=======
    with patch("app.services.oauth_daemon.settings") as mock_settings, \
         patch("app.services.oauth_daemon.Credentials") as mock_creds_class, \
         patch("app.services.oauth_daemon.asyncio.to_thread") as mock_to_thread:

        mock_settings.GOOGLE_CLIENT_ID = "client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client_secret"

        mock_creds_instance = MagicMock()
        mock_creds_instance.token = "new_access"
        mock_creds_instance.refresh_token = "new_refresh"
        mock_creds_instance.expiry = now + timedelta(hours=1)
        mock_creds_class.return_value = mock_creds_instance

        # mock the to_thread async call instead of normal instance method since it is awaited
        async def mock_refresh(*args, **kwargs):
            return
        mock_to_thread.side_effect = mock_refresh

        await refresh_google_token(cred, db_session)

        await db_session.refresh(cred)
        assert decrypt_key(cred.encrypted_access_token) == "new_access"
        assert decrypt_key(cred.encrypted_refresh_token) == "new_refresh"

        expires_at = cred.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        assert expires_at > now
>>>>>>> 9b1d119 (no-mistakes(document): Updated documentation and lint for OAuth refresh daemon)

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
        is_valid=True,
    )
    db_session.add(cred)
    await db_session.commit()

<<<<<<< HEAD
    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh_token = "valid_refresh_token"
        mock_instance.refresh.side_effect = Exception("Auth Error")
=======
    with patch("app.services.oauth_daemon.settings") as mock_settings:
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""

        await refresh_google_token(cred, db_session)

        await db_session.refresh(cred)
        assert decrypt_key(cred.encrypted_access_token) == old_access
>>>>>>> 9b1d119 (no-mistakes(document): Updated documentation and lint for OAuth refresh daemon)

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
        is_valid=True,
    )
    db_session.add(cred)
    await db_session.commit()

<<<<<<< HEAD
    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        await refresh_tokens(db_session)
        # Should not be called because it's not expiring soon
        MockCreds.assert_not_called()
=======
    with patch("app.services.oauth_daemon.settings") as mock_settings, \
         patch("app.services.oauth_daemon.Credentials") as mock_creds_class, \
         patch("app.services.oauth_daemon.asyncio.to_thread") as mock_to_thread:

        mock_settings.GOOGLE_CLIENT_ID = "client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client_secret"

        mock_creds_instance = MagicMock()
        mock_creds_class.return_value = mock_creds_instance

        async def throw_exception(*args, **kwargs):
            raise Exception("Auth failed")

        mock_to_thread.side_effect = throw_exception

        await refresh_google_token(cred, db_session)

        await db_session.refresh(cred)
        assert decrypt_key(cred.encrypted_access_token) == old_access
>>>>>>> 9b1d119 (no-mistakes(document): Updated documentation and lint for OAuth refresh daemon)
