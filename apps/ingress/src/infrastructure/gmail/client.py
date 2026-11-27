"""Gmail API Client wrapper."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import logging
import os
from typing import Any
import uuid

from apps.ingress.src.domain.interfaces import EmailClient, IngressRepository

logger = logging.getLogger(__name__)


def mask_email(email: str | None) -> str:
    """Mask email for privacy in logs (e.g. user@example.com -> u***@example.com)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


class GmailClient(EmailClient):
    """Client for reading emails via Google Gmail API."""

    def __init__(
        self,
        service: Any = None,
        credentials: Any = None,
        household_id: uuid.UUID | None = None,
        credential_id: int | None = None,
        repo: IngressRepository | None = None,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
    ):
        self._service = service
        self._credentials = credentials
        self.household_id = household_id
        self.credential_id = credential_id
        self.repo = repo
        self.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", credentials_path)
        self.token_path = os.getenv("GMAIL_TOKEN_PATH", token_path)

    @classmethod
    async def for_household(
        cls,
        household_id: uuid.UUID,
        repo: IngressRepository,
    ) -> GmailClient | None:
        """Construct per-household client from DB oauth_credentials, or fallback to file."""
        from google.oauth2.credentials import Credentials
        from app.core.config import settings
        from app.core.crypto import decrypt_key

        db_cred = await repo.get_oauth_credential(household_id=household_id, source="gmail")
        if db_cred:
            masked = mask_email(db_cred.account_email)
            logger.info("Found DB OAuth credential for household=%s account=%s", household_id, masked)
            try:
                decrypted_access = decrypt_key(db_cred.encrypted_access_token)
                decrypted_refresh = decrypt_key(db_cred.encrypted_refresh_token) if db_cred.encrypted_refresh_token else None

                client_id = getattr(settings, "GOOGLE_CLIENT_ID", "") or os.getenv("GOOGLE_CLIENT_ID", "")
                client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "") or os.getenv("GOOGLE_CLIENT_SECRET", "")
                token_uri = "https://oauth2.googleapis.com/token"

                expiry = db_cred.expires_at
                if expiry is not None and expiry.tzinfo is not None:
                    expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

                creds = Credentials(
                    token=decrypted_access,
                    refresh_token=decrypted_refresh,
                    token_uri=token_uri,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=db_cred.scopes,
                    expiry=expiry,
                )

                return cls(
                    credentials=creds,
                    household_id=household_id,
                    credential_id=db_cred.id,
                    repo=repo,
                )
            except Exception as e:
                logger.error("Failed to decrypt or construct DB credentials for household=%s: %s", household_id, e)
                return None

        # Fallback to token file
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        if os.path.exists(token_path):
            logger.info("Using file fallback token at %s for household=%s", token_path, household_id)
            try:
                creds = Credentials.from_authorized_user_file(token_path)
                return cls(
                    credentials=creds,
                    household_id=household_id,
                    repo=repo,
                    token_path=token_path,
                )
            except Exception as e:
                logger.warning("Failed to load file fallback token at %s: %s", token_path, e)

        logger.warning("No OAuth credential or token file found for household=%s. Skipping.", household_id)
        return None

    def _ensure_service(self) -> Any:
        if self._service is not None:
            return self._service

        from googleapiclient.discovery import build

        if self._credentials is not None:
            self._service = build("gmail", "v1", credentials=self._credentials)
            return self._service

        from google.oauth2.credentials import Credentials

        if os.path.exists(self.token_path):
            self._credentials = Credentials.from_authorized_user_file(self.token_path)
            self._service = build("gmail", "v1", credentials=self._credentials)
            return self._service

        raise FileNotFoundError(f"OAuth token file not found at {self.token_path}")

    async def _refresh_if_expired(self) -> None:
        """Check credentials expiry, refresh if expired, and persist back to DB."""
        if self._credentials is None:
            return

        is_expired = False
        try:
            is_expired = bool(self._credentials.expired)
        except Exception:
            is_expired = False

        if is_expired:
            logger.info("Credentials expired for household=%s, refreshing token...", self.household_id)
            from google.auth.transport.requests import Request
            await asyncio.to_thread(self._credentials.refresh, Request())

            if self.repo is not None and self.credential_id is not None:
                from app.core.crypto import encrypt_key
                encrypted_access = encrypt_key(self._credentials.token)
                encrypted_refresh = encrypt_key(self._credentials.refresh_token) if self._credentials.refresh_token else None
                new_expiry = self._credentials.expiry
                if new_expiry is not None:
                    if new_expiry.tzinfo is None:
                        new_expiry = new_expiry.replace(tzinfo=timezone.utc)
                else:
                    new_expiry = datetime.now(timezone.utc)

                await self.repo.update_oauth_credential(
                    credential_id=self.credential_id,
                    encrypted_access_token=encrypted_access,
                    expires_at=new_expiry,
                    encrypted_refresh_token=encrypted_refresh,
                )
                logger.info("Persisted refreshed credentials for household=%s to DB", self.household_id)

    def build_email_url(self, raw_message_id: str | None) -> str | None:
        if not raw_message_id or not str(raw_message_id).strip():
            return None
        return f"https://mail.google.com/mail/u/0/#all/{raw_message_id.strip()}"

    def extract_body(self, payload: dict[str, Any]) -> str:
        """Extract text from MIME message payload."""
        if not payload:
            return ""

        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")

        if mime_type == "text/plain" and body_data:
            try:
                return base64.urlsafe_b64decode(body_data.encode("utf-8")).decode("utf-8")
            except Exception:
                pass

        parts = payload.get("parts", [])
        for part in parts:
            text = self.extract_body(part)
            if text:
                return text

        if body_data:
            try:
                return base64.urlsafe_b64decode(body_data.encode("utf-8")).decode("utf-8", errors="replace")
            except Exception:
                pass

        return ""

    async def fetch_alert_messages(
        self,
        query: str = "label:INBOX",
        after_internal_date: int | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        await self._refresh_if_expired()
        service = self._ensure_service()
        full_query = query
        if after_internal_date:
            full_query += f" after:{after_internal_date // 1000}"

        def _execute_list():
            return service.users().messages().list(userId="me", q=full_query, maxResults=max_results).execute()

        results = await asyncio.to_thread(_execute_list)
        messages = results.get("messages", [])
        detailed_messages: list[dict[str, Any]] = []

        for msg_meta in messages:
            msg_id = msg_meta["id"]

            def _execute_get(mid=msg_id):
                return service.users().messages().get(userId="me", id=mid, format="full").execute()

            msg = await asyncio.to_thread(_execute_get)
            body_text = self.extract_body(msg.get("payload", {}))
            detailed_messages.append({
                "id": msg_id,
                "internalDate": int(msg.get("internalDate", 0)),
                "snippet": msg.get("snippet", ""),
                "text": body_text or msg.get("snippet", ""),
            })
        return detailed_messages

