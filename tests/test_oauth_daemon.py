from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.crypto import decrypt_key, encrypt_key
from app.services.oauth_daemon import refresh_tokens

@pytest.mark.asyncio
async def test_refresh_tokens_success(db_session, unique_user_alice):
    user = await db_session.get_or_create_user(unique_user_alice)
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    cred = await db_session.add_oauth_credential(
        user_id=user.id,
        source="gmail",
        encrypted_access_token=encrypt_key("old_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=expired_time,
        is_valid=True,
    )

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh_token = "valid_refresh_token"
        mock_instance.token = "new_access_token"
        mock_instance.expiry = now + timedelta(hours=1)

        MockCreds.return_value = mock_instance

        await refresh_tokens(db_session)
        mock_instance.refresh.assert_called_once()

    # Verify DB was updated
    expiring = await db_session.get_expiring_oauth_credentials(now + timedelta(hours=2))
    updated_cred = next(c for c in expiring if c.id == cred.id)
    assert decrypt_key(updated_cred.encrypted_access_token) == "new_access_token"
    assert updated_cred.expires_at.replace(tzinfo=timezone.utc) > now

@pytest.mark.asyncio
async def test_refresh_tokens_error_handling(db_session, unique_user_alice, caplog):
    user = await db_session.get_or_create_user(unique_user_alice)
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    cred = await db_session.add_oauth_credential(
        user_id=user.id,
        source="gmail",
        encrypted_access_token=encrypt_key("old_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=expired_time,
        is_valid=True,
    )

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        mock_instance = MagicMock()
        mock_instance.refresh.side_effect = Exception("Google Auth Server Error")
        MockCreds.return_value = mock_instance

        await refresh_tokens(db_session)

    # Invalidate credential
    expiring = await db_session.get_expiring_oauth_credentials(now + timedelta(hours=2))
    updated = next((c for c in expiring if c.id == cred.id), None)
    assert updated is None  # Since is_valid is now False, get_expiring (WHERE is_valid=TRUE) won't return it

@pytest.mark.asyncio
async def test_refresh_tokens_skips_valid(db_session, unique_user_alice):
    user = await db_session.get_or_create_user(unique_user_alice)
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(hours=2)

    await db_session.add_oauth_credential(
        user_id=user.id,
        source="gmail",
        encrypted_access_token=encrypt_key("valid_access_token"),
        encrypted_refresh_token=encrypt_key("valid_refresh_token"),
        expires_at=future_time,
        is_valid=True,
    )

    with patch("app.services.oauth_daemon.Credentials") as MockCreds:
        await refresh_tokens(db_session)
        MockCreds.assert_not_called()
