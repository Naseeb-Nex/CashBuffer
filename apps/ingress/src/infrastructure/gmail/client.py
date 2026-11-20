"""Gmail API Client wrapper."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from apps.ingress.src.domain.interfaces import EmailClient

logger = logging.getLogger(__name__)

class GmailClient(EmailClient):
    """Client for reading emails via Google Gmail API."""

    def __init__(self, service: Any = None, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self._service = service
        self.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", credentials_path)
        self.token_path = os.getenv("GMAIL_TOKEN_PATH", token_path)

    def _get_service(self) -> Any:
        if self._service is not None:
            return self._service

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path)
            self._service = build("gmail", "v1", credentials=creds)
            return self._service
        raise FileNotFoundError(f"OAuth token file not found at {self.token_path}")

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
        service = self._get_service()
        full_query = query
        if after_internal_date:
            full_query += f" after:{after_internal_date // 1000}"

        try:
            results = service.users().messages().list(userId="me", q=full_query, maxResults=max_results).execute()
            messages = results.get("messages", [])
            detailed_messages: list[dict[str, Any]] = []

            for msg_meta in messages:
                msg_id = msg_meta["id"]
                msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                body_text = self.extract_body(msg.get("payload", {}))
                detailed_messages.append({
                    "id": msg_id,
                    "internalDate": int(msg.get("internalDate", 0)),
                    "snippet": msg.get("snippet", ""),
                    "text": body_text or msg.get("snippet", ""),
                })
            return detailed_messages
        except Exception as e:
            logger.error("Error fetching Gmail messages: %s", e)
            return []
