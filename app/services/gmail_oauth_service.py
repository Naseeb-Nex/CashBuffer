"""Gmail OAuth Service: handles 3-legged OAuth flow, state verification, token exchange, and credentials lifecycle."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.crypto import decrypt_key, encrypt_key
from app.infrastructure.persistence.native_repository import NativeRepository

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

def mask_email(email: str | None) -> str:
    """Mask email for privacy in logs (e.g., u***r@example.com)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"

class GmailOAuthService:
    def __init__(self, repo: NativeRepository):
        self.repo = repo

    def get_state_secret(self) -> str:
        """Derive state secret from dedicated env var or fallback to HMAC from ENCRYPTION_KEY."""
        if settings.GMAIL_OAUTH_STATE_SECRET:
            return settings.GMAIL_OAUTH_STATE_SECRET
        return hmac.new(
            settings.ENCRYPTION_KEY.encode("utf-8"),
            b"gmail_oauth_state",
            hashlib.sha256,
        ).hexdigest()

    def generate_state(self, user_id: str, household_id: str) -> str:
        """Generate signed state token containing user_id, household_id, nonce, and 10-minute expiry."""
        secret = self.get_state_secret()
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "household_id": household_id,
            "nonce": secrets.token_urlsafe(16),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def verify_state(self, state: str) -> dict[str, Any]:
        """Verify signature and expiry of OAuth state token."""
        secret = self.get_state_secret()
        try:
            payload = jwt.decode(
                state,
                secret,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            if not payload.get("user_id") or not payload.get("household_id"):
                raise ValueError("State payload missing user_id or household_id")
            return payload
        except Exception as e:
            logger.warning("Invalid OAuth state: %s", e)
            raise ValueError(f"State verification failed: {e}") from e

    async def get_status(self, household_id: str) -> dict[str, Any]:
        """Fetch current Gmail connection status for household."""
        cred = await self.repo.get_oauth_credential_by_household(household_id, "gmail")
        config = await self.repo.get_ingress_config_by_household(household_id, "gmail")

        last_synced_at = None
        interval_minutes = 60
        is_enabled = False

        if config:
            if config.get("last_run_at"):
                last_synced_at = config["last_run_at"].isoformat()
            interval_minutes = int(config.get("interval_minutes", 60))
            is_enabled = bool(config.get("is_enabled", False))

        if not cred:
            return {
                "connected": False,
                "status": "not_connected",
                "account_email": None,
                "last_synced_at": last_synced_at,
                "interval_minutes": interval_minutes,
                "is_enabled": is_enabled,
            }

        if not cred.is_valid:
            return {
                "connected": False,
                "status": "needs_reconnect",
                "account_email": cred.account_email,
                "last_synced_at": last_synced_at,
                "interval_minutes": interval_minutes,
                "is_enabled": is_enabled,
            }

        return {
            "connected": True,
            "status": "connected",
            "account_email": cred.account_email,
            "last_synced_at": last_synced_at,
            "interval_minutes": interval_minutes,
            "is_enabled": is_enabled,
        }

    async def get_authorize_url(self, user_id: str, household_id: str) -> str:
        """Build Google 3-legged OAuth consent URL."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "gmail_not_configured",
                    "message": "Gmail connect is not configured on the server",
                },
            )

        state = self.generate_state(user_id=user_id, household_id=household_id)
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def handle_callback(
        self,
        code: str | None,
        state: str | None,
        error: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> str:
        """
        Handle callback redirect from Google.
        Returns destination URL on frontend WEB_BASE_URL.
        """
        base_web_url = settings.WEB_BASE_URL.rstrip("/")

        if error:
            logger.warning("OAuth callback received error: %s", error)
            return f"{base_web_url}/settings?error={error}"

        if not state:
            return f"{base_web_url}/settings?error=invalid_state"

        try:
            state_data = self.verify_state(state)
        except Exception:
            return f"{base_web_url}/settings?error=invalid_state"

        user_id = state_data["user_id"]
        household_id = state_data["household_id"]

        if not code:
            return f"{base_web_url}/settings?error=missing_code"

        # Exchange code for tokens
        token_endpoint = "https://oauth2.googleapis.com/token"
        token_payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

        async def _exchange():
            if http_client:
                return await http_client.post(token_endpoint, data=token_payload)
            async with httpx.AsyncClient(timeout=15.0) as client:
                return await client.post(token_endpoint, data=token_payload)

        try:
            token_resp = await _exchange()
        except Exception as e:
            logger.error("Token exchange network error: %s", e)
            return f"{base_web_url}/settings?error=token_exchange_failed"

        if token_resp.status_code != 200:
            logger.error("Token exchange failed with status %d", token_resp.status_code)
            return f"{base_web_url}/settings?error=token_exchange_failed"

        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        refresh_token = token_json.get("refresh_token")
        expires_in = token_json.get("expires_in", 3600)
        scopes = token_json.get("scope", "").split() if token_json.get("scope") else GMAIL_SCOPES

        if not access_token:
            return f"{base_web_url}/settings?error=token_exchange_failed"

        # Handle missing refresh token: reuse stored refresh token or fail
        existing_cred = await self.repo.get_oauth_credential_by_household(household_id, "gmail")
        if not refresh_token:
            if existing_cred and existing_cred.encrypted_refresh_token:
                encrypted_refresh = existing_cred.encrypted_refresh_token
            else:
                logger.warning("No refresh token returned by Google and none stored for household %s", household_id)
                return f"{base_web_url}/settings?error=no_refresh_token"
        else:
            encrypted_refresh = encrypt_key(refresh_token)

        encrypted_access = encrypt_key(access_token)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Fetch email from userinfo
        account_email = None
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

        async def _fetch_userinfo():
            headers = {"Authorization": f"Bearer {access_token}"}
            if http_client:
                return await http_client.get(userinfo_endpoint, headers=headers)
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.get(userinfo_endpoint, headers=headers)

        try:
            userinfo_resp = await _fetch_userinfo()
            if userinfo_resp.status_code == 200:
                userinfo_json = userinfo_resp.json()
                account_email = userinfo_json.get("email")
        except Exception as e:
            logger.warning("Failed to fetch userinfo email: %s", e)

        # Upsert encrypted credentials
        await self.repo.upsert_oauth_credential(
            user_id=user_id,
            household_id=household_id,
            source="gmail",
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            expires_at=expires_at,
            account_email=account_email,
            scopes=scopes,
            is_valid=True,
        )

        # Ensure ingress config is enabled
        await self.repo.ensure_ingress_config_enabled(
            household_id=household_id,
            user_id=user_id,
            provider="gmail",
        )

        logger.info(
            "Successfully connected Gmail for household %s, account %s",
            household_id,
            mask_email(account_email),
        )
        return f"{base_web_url}/settings?gmail=connected"

    async def disconnect(
        self,
        user_id: str,
        household_id: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Disconnect Gmail: owner only, revoke at Google, invalidate in DB."""
        role = await self.repo.get_household_member_role(household_id=household_id, user_id=user_id)
        if role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the household owner can disconnect Gmail",
            )

        # Best-effort revocation
        existing_cred = await self.repo.get_oauth_credential_by_household(household_id, "gmail")
        if existing_cred and existing_cred.encrypted_access_token:
            try:
                raw_token = decrypt_key(existing_cred.encrypted_access_token)
                revoke_endpoint = "https://oauth2.googleapis.com/revoke"

                async def _revoke():
                    if http_client:
                        return await http_client.post(revoke_endpoint, params={"token": raw_token})
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        return await client.post(revoke_endpoint, params={"token": raw_token})

                await _revoke()
            except Exception as e:
                logger.warning("Token revoke request failed (best-effort): %s", e)

        # Invalidate in DB and disable ingress config
        await self.repo.disconnect_oauth_credential(household_id=household_id, source="gmail")
        logger.info("Gmail disconnected for household %s by owner %s", household_id, user_id)
