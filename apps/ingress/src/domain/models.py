"""Domain models for Ingress microservice."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
import uuid

@dataclass
class IngressJob:
    """Represents a scheduled ingress synchronization task."""

    id: uuid.UUID
    household_id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    interval_minutes: int
    next_run_at: datetime
    status: str

@dataclass
class ParsedAlert:
    """Represents an extracted financial transaction from a bank alert."""

    amount: float
    currency: str
    is_inflow: bool
    record_date: date
    vendor_raw: str
    raw_email_id: str | None = None
    email_url: str | None = None
    notes: str | None = None
    status: str = "parsed"
    raw_source: str = "gmail_axis"

    def compute_dedupe_hash(self, household_id: str | uuid.UUID) -> str:
        """Computes SHA-256 dedupe hash: household_id + record_date + amount + vendor_raw."""
        payload = f"{str(household_id).strip()}:{self.record_date.isoformat()}:{self.amount:.2f}:{self.vendor_raw.strip().upper()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

@dataclass
class SyncCheckpoint:
    """Represents checkpoint state for an ingress sync."""

    household_id: uuid.UUID
    last_history_id: str | None = None
    last_email_internal_date: int | None = None
    total_processed: int = 0
    updated_at: datetime | None = None


@dataclass
class OAuthCredential:
    """OAuth credential entity loaded from oauth_credentials table."""

    id: int
    user_id: uuid.UUID
    household_id: uuid.UUID | None
    source: str
    encrypted_access_token: str
    encrypted_refresh_token: str
    expires_at: datetime
    is_valid: bool = True
    account_email: str | None = None
    scopes: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

