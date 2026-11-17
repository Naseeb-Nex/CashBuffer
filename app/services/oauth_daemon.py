import asyncio
import logging
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import settings
from app.core.crypto import decrypt_key, encrypt_key
from app.infrastructure.persistence.db_pool import get_db_pool
from app.infrastructure.persistence.native_repository import NativeRepository

logger = logging.getLogger(__name__)

async def refresh_tokens(db: NativeRepository):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(minutes=15)

    creds_to_refresh = await db.get_expiring_oauth_credentials(cutoff)

    for db_cred in creds_to_refresh:
        if db_cred.source == "gmail":
            token_uri = "https://oauth2.googleapis.com/token"
            client_id = settings.GOOGLE_CLIENT_ID
            client_secret = settings.GOOGLE_CLIENT_SECRET
        else:
            token_uri = getattr(settings, f"{db_cred.source.upper()}_TOKEN_URI", "")
            client_id = getattr(settings, f"{db_cred.source.upper()}_CLIENT_ID", "")
            client_secret = getattr(settings, f"{db_cred.source.upper()}_CLIENT_SECRET", "")
            if not token_uri:
                logger.warning(f"Missing OAuth config for source {db_cred.source}")
                continue

        access_token = decrypt_key(db_cred.encrypted_access_token)
        refresh_token = decrypt_key(db_cred.encrypted_refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
        )

        if refresh_token:
            try:
                await asyncio.to_thread(creds.refresh, Request())
                encrypted_access = encrypt_key(creds.token)
                expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else now + timedelta(hours=1)
                await db.update_oauth_credential(
                    cred_id=db_cred.id,
                    encrypted_access_token=encrypted_access,
                    expires_at=expiry,
                    is_valid=True,
                )
                logger.info(f"Successfully refreshed token for OAuth credential ID {db_cred.id}")
            except Exception as e:
                logger.error(f"Failed to refresh token for OAuth credential ID {db_cred.id}: {e}")
                await db.update_oauth_credential(
                    cred_id=db_cred.id,
                    encrypted_access_token=db_cred.encrypted_access_token,
                    expires_at=db_cred.expires_at,
                    is_valid=False,
                )
        else:
            logger.warning(f"No refresh token available for credential ID {db_cred.id}")
            await db.update_oauth_credential(
                cred_id=db_cred.id,
                encrypted_access_token=db_cred.encrypted_access_token,
                expires_at=db_cred.expires_at,
                is_valid=False,
            )

async def oauth_refresh_daemon_loop(poll_interval: int = 300):
    logger.info("OAuth Refresh Daemon started.")
    while True:
        try:
            pool = await get_db_pool()
            if pool is not None:
                repo = NativeRepository(pool)
                await refresh_tokens(repo)
        except Exception as e:
            logger.error(f"Error in OAuth refresh daemon: {e}")
        await asyncio.sleep(poll_interval)
