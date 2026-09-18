import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.db.database import AsyncSessionLocal
from app.db.models import OAuthCredential
from app.core.crypto import encrypt_key, decrypt_key
from app.core.config import settings

logger = logging.getLogger(__name__)

async def refresh_tokens(db: AsyncSession):
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(minutes=15)
    
    result = await db.execute(
        select(OAuthCredential).where(
            OAuthCredential.expires_at < cutoff,
            OAuthCredential.is_valid == True
        )
    )
    creds_to_refresh = result.scalars().all()

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
                # refresh() does blocking sync request, so we should run it in executor
                await asyncio.to_thread(creds.refresh, Request())

                db_cred.encrypted_access_token = encrypt_key(creds.token)
                db_cred.expires_at = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else (now + timedelta(hours=1))

                db.add(db_cred)
                logger.info(f"Successfully refreshed OAuth token for user {db_cred.user_id} source {db_cred.source}")
            except Exception as e:
                logger.error(f"Failed to refresh OAuth token for user {db_cred.user_id} source {db_cred.source}: {e}")
                db_cred.is_valid = False
                db.add(db_cred)
                
    await db.commit()

async def oauth_refresh_daemon_loop():
    """Background task to continuously monitor and refresh OAuth tokens."""
    logger.info("OAuth Refresh Daemon started.")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await refresh_tokens(db)
        except asyncio.CancelledError:
            logger.info("OAuth Refresh Daemon shutting down.")
            break
        except Exception as e:
            logger.error(f"OAuth Refresh Daemon encountered an error: {e}")
            
        await asyncio.sleep(60 * 5)  # Check every 5 minutes
