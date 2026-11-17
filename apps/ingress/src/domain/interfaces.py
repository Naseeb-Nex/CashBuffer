"""Domain interfaces for Ingress microservice."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import uuid

from apps.ingress.src.domain.models import IngressJob, ParsedAlert, SyncCheckpoint

class EmailClient(ABC):
    """Abstract interface for email fetching clients (e.g. Gmail)."""

    @abstractmethod
    async def fetch_alert_messages(
        self,
        query: str = "label:INBOX",
        after_internal_date: int | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch raw messages matching criteria."""
        pass

    @abstractmethod
    def build_email_url(self, raw_message_id: str | None) -> str | None:
        """Generate web URL for viewing the email."""
        pass

class AlertParser(ABC):
    """Abstract interface for parsing email text into structured transactions."""

    @abstractmethod
    def parse(self, text: str, raw_email_id: str | None = None) -> ParsedAlert | None:
        """Parses email content into a ParsedAlert or None if unrecognized."""
        pass

class IngressRepository(ABC):
    """Abstract interface for persisting ingress data via pure SQL."""

    @abstractmethod
    async def fetch_due_jobs(self) -> list[IngressJob]:
        """Fetch jobs where next_run_at <= CURRENT_TIMESTAMP and is_enabled = TRUE."""
        pass

    @abstractmethod
    async def save_transaction(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        alert: ParsedAlert,
    ) -> bool:
        """Insert transaction with dedupe protection. Returns True if inserted, False if duplicate."""
        pass

    @abstractmethod
    async def quarantine_email(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        raw_email_id: str | None,
        email_url: str | None,
        email_text: str,
        error_reason: str,
    ) -> None:
        """Record unparseable or erroring alert into quarantined_emails."""
        pass

    @abstractmethod
    async def get_checkpoint(self, household_id: uuid.UUID) -> SyncCheckpoint | None:
        """Get current sync checkpoint for a household."""
        pass

    @abstractmethod
    async def update_checkpoint(
        self,
        household_id: uuid.UUID,
        last_email_internal_date: int | None,
        increment_processed: int = 1,
    ) -> None:
        """Update or create sync checkpoint for a household."""
        pass

    @abstractmethod
    async def mark_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
        interval_minutes: int,
        error: str | None = None,
    ) -> None:
        """Update job status and set next_run_at."""
        pass
