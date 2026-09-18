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
            OAuthCredential.expires_at < cutoff
        )
    )
    creds_to_refresh = result.scalars().all()
    
    for db_cred in creds_to_refresh:
        # We only support gmail/google rotation right now
        if db_cred.source != "gmail":
            continue
            
        access_token = decrypt_key(db_cred.encrypted_access_token)
        refresh_token = decrypt_key(db_cred.encrypted_refresh_token)
        
        google_creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        
        if google_creds.expired and google_creds.refresh_token:
            try:
                # refresh() does blocking sync request, so we should run it in executor
                await asyncio.to_thread(google_creds.refresh, Request())
                
                db_cred.encrypted_access_token = encrypt_key(google_creds.token)
                db_cred.expires_at = google_creds.expiry.replace(tzinfo=timezone.utc) if google_creds.expiry else (now + timedelta(hours=1))
                
                db.add(db_cred)
                logger.info(f"Successfully refreshed Google OAuth token for user {db_cred.user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh Google OAuth token for user {db_cred.user_id}: {e}")
                
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
