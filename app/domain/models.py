from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

class TransactionStatus(str, Enum):
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    CATEGORIZED = "categorized"

@dataclass
class User:
    id: str  # Internal UUID string
    idp_user_id: str  # External subject / identity string
    email: str | None = None
    telegram_chat_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

@dataclass
class Household:
    id: str
    name: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

@dataclass
class Category:
    id: int
    user_id: str
    name: str
    household_id: str | None = None
    parent_id: int | None = None
    created_at: datetime | None = None

@dataclass
class VendorRule:
    id: int
    user_id: str
    vendor_regex: str
    default_category_id: int
    household_id: str | None = None
    created_at: datetime | None = None

@dataclass
class Transaction:
    id: int
    user_id: str
    amount: float
    currency: str = "INR"
    is_inflow: bool = False
    record_date: date = field(default_factory=date.today)
    vendor_raw: str = "Unknown"
    category_id: int | None = None
    status: TransactionStatus = TransactionStatus.PARSED
    tx_hash: str | None = None
    dedupe_hash: str | None = None
    household_id: str | None = None
    raw_source: str | None = "gmail_axis"
    raw_email_id: str | None = None
    email_url: str | None = None
    created_at: datetime | None = None

@dataclass
class OAuthCredential:
    id: int
    user_id: str
    source: str
    encrypted_access_token: str
    encrypted_refresh_token: str
    expires_at: datetime
    is_valid: bool = True
    household_id: str | None = None
    account_email: str | None = None
    scopes: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

@dataclass
class LLMConfig:
    user_id: str
    provider: str
    model_name: str
    encrypted_key: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

@dataclass
class QuarantinedEmail:
    id: int
    email_text: str
    error_reason: str
    user_id: str | None = None
    household_id: str | None = None
    raw_email_id: str | None = None
    email_url: str | None = None
    ingress_payload_id: str | None = None
    resolved: bool = False
    created_at: datetime | None = None
    resolved_at: datetime | None = None
