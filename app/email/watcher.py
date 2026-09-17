import base64
import logging
from typing import Any

from googleapiclient.discovery import build

from app.email.parser import UnifiedBankParser

logger = logging.getLogger(__name__)


def get_gmail_service(creds):
    """Builds the Gmail service using provided credentials."""
    return build("gmail", "v1", credentials=creds)


def search_recent_bank_alerts(
    service,
    sender_email: str = "alerts@axis.bank.in",
    newer_than: str = "2m",
    limit: int = 50,
) -> list[dict[str, str]]:
    """
    Finds alert emails matching query.
    """
    query = f"from:{sender_email} newer_than:{newer_than}"
    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
        return results.get("messages", [])
    except Exception as e:
        logger.error(f"Failed to query Gmail messages: {e}")
        return []


def get_email_body(service, msg_id: str) -> str | None:
    """
    Fetches the full email message and decodes the plain text body.
    """
    try:
        message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        payload = message.get("payload", {})
        parts = payload.get("parts", [])

        if not parts:
            data = payload.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8")
            return None

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8")

        return None
    except Exception as e:
        logger.error(f"Failed to retrieve email body for message {msg_id}: {e}")
        return None


def mark_as_read(service, msg_id: str) -> None:
    """Removes UNREAD label from a message."""
    try:
        service.users().messages().batchModify(
            userId="me",
            body={"ids": [msg_id], "removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception as e:
        logger.error(f"Failed to mark message {msg_id} as read: {e}")


def parse_email_message(service, msg_id: str) -> dict[str, Any] | None:
    """Fetches and parses a single Gmail message into structured transaction data."""
    body = get_email_body(service, msg_id)
    if not body:
        return None
    return UnifiedBankParser.parse(body)
