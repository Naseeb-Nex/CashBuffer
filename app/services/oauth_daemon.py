import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from google.auth.exceptions import RefreshError
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
    threshold = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with AsyncSessionLocal() as session:
        # Find credentials expiring in the next 15 minutes, or already expired,
        # that have a refresh token.
        stmt = select(OAuthCredential.id).where(
            and_(
                OAuthCredential.encrypted_refresh_token.isnot(None),
                OAuthCredential.is_valid.is_(True),
                or_(
                    OAuthCredential.expires_at.is_(None),
                    OAuthCredential.expires_at <= threshold
                )
            )
        )
        result = await session.execute(stmt)
        cred_ids = result.scalars().all()

    for chunk in [cred_ids[i:i+100] for i in range(0, len(cred_ids), 100)]:
        for cred_id in chunk:
            async with AsyncSessionLocal() as session:
                db_cred = await session.get(OAuthCredential, cred_id)
                if not db_cred or not db_cred.is_valid:
                    continue
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

                    else:
                        # generalized refresh for any other configured provider
                        provider_upper = db_cred.provider.upper()
                        token_uri = getattr(settings, f"{provider_upper}_TOKEN_URI", None)
                        client_id = getattr(settings, f"{provider_upper}_CLIENT_ID", None)
                        client_secret = getattr(settings, f"{provider_upper}_CLIENT_SECRET", None)

                        if not token_uri or not client_id or not client_secret:
                            raise ValueError(f"Missing OAuth config for {db_cred.provider}")

                        async with httpx.AsyncClient() as client:
                            resp = await client.post(token_uri, data={
                                "grant_type": "refresh_token",
                                "refresh_token": db_cred.refresh_token,
                                "client_id": client_id,
                                "client_secret": client_secret,
                            })
                            resp.raise_for_status()
                            data = resp.json()
                            db_cred.access_token = data["access_token"]
                            if "refresh_token" in data:
                                db_cred.refresh_token = data["refresh_token"]
                            if "expires_in" in data:
                                db_cred.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

                    await session.commit()
                    logger.info(f"Refreshed token for user {db_cred.user_id} provider {db_cred.provider}")

                except Exception as e:
                    logger.error(f"Failed to refresh token for idx {cred_id}: {e}")
                    is_permanent = False
                    if isinstance(e, RefreshError):
                        is_permanent = True
                    elif isinstance(e, httpx.HTTPStatusError) and 400 <= e.response.status_code < 500:
                        is_permanent = True
                    elif isinstance(e, ValueError):
                        is_permanent = True

                    if is_permanent:
                        db_cred.is_valid = False
                        await session.commit()
                    else:
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
