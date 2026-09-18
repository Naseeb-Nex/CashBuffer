import asyncio
import logging
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy import and_, or_, select

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import OAuthCredential

logger = logging.getLogger(__name__)

# Control flag so we can cleanly stop the daemon
_stop_event = asyncio.Event()

async def refresh_credentials():
    """
    Main loop to find and refresh expiring credentials.
    """
    async with AsyncSessionLocal() as session:
        # Find credentials expiring in the next 15 minutes, or already expired,
        # that have a refresh token.
        threshold = datetime.now(timezone.utc) + timedelta(minutes=15)

        stmt = select(OAuthCredential).where(
            and_(
                OAuthCredential.refresh_token.isnot(None),
                or_(
                    OAuthCredential.expires_at.is_(None),
                    OAuthCredential.expires_at <= threshold
                )
            )
        )
        result = await session.execute(stmt)
        creds = result.scalars().all()

        for db_cred in creds:
            try:
                if db_cred.provider == "google":
                    cred_obj = Credentials(
                        token=db_cred.access_token,
                        refresh_token=db_cred.refresh_token,
                        client_id=settings.GOOGLE_CLIENT_ID,
                        client_secret=settings.GOOGLE_CLIENT_SECRET,
                        token_uri="https://oauth2.googleapis.com/token",
                    )
                    # We have to wrap the sync Request in an executor since google-auth is synchronous
                    await asyncio.to_thread(cred_obj.refresh, Request())

                    db_cred.access_token = cred_obj.token
                    if cred_obj.refresh_token:
                        db_cred.refresh_token = cred_obj.refresh_token
                    if cred_obj.expiry:
                        db_cred.expires_at = cred_obj.expiry.replace(tzinfo=timezone.utc)

                    await session.commit()
                    logger.info(f"Refreshed token for user {db_cred.user_id} provider {db_cred.provider}")
                else:
                    # other providers (plaid, etc.)
                    pass
            except Exception as e:
                logger.error(f"Failed to refresh token for user {db_cred.user_id} provider {db_cred.provider}: {e}")
                await session.rollback()

async def start_oauth_refresh_daemon(interval_seconds: int = 300):
    logger.info("Starting OAuth refresh daemon")
    _stop_event.clear()
    while not _stop_event.is_set():
        try:
            await refresh_credentials()
        except Exception as e:
            logger.error(f"Error in OAuth refresh daemon: {e}")

        # Sleep for interval_seconds but allow cancellation via _stop_event
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass # normal interval

async def stop_oauth_refresh_daemon(task: asyncio.Task = None):
    logger.info("Stopping OAuth refresh daemon")
    _stop_event.set()
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
