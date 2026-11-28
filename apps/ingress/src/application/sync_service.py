"""Ingress synchronization service orchestrating fetch -> parse -> dedupe -> insert."""

from __future__ import annotations

import logging
from typing import Any

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from apps.ingress.src.domain.interfaces import AlertParser, EmailClient, IngressRepository
from apps.ingress.src.domain.models import IngressJob
from apps.ingress.src.infrastructure.gmail.client import (
    GmailClient,
    OAuthDecryptionError,
)

logger = logging.getLogger(__name__)


def is_auth_error(exc: Exception) -> bool:
    """Check if exception represents an OAuth token revocation, auth failure, or decrypt failure."""
    if isinstance(exc, (RefreshError, OAuthDecryptionError)):
        return True
    if isinstance(exc, HttpError):
        if getattr(exc, "status_code", None) in (401, 403) or (
            getattr(exc, "resp", None) is not None and exc.resp.status in (401, 403)
        ):
            return True
    err_str = str(exc).lower()
    if (
        "invalid_grant" in err_str
        or "token has been expired or revoked" in err_str
        or "reconnection required" in err_str
        or "failed to decrypt" in err_str
    ):
        return True
    return False


class IngressSyncService:
    """Coordinates parsing, deduplication, transaction persistence, and error quarantine."""

    def __init__(
        self,
        repository: IngressRepository,
        email_client: EmailClient | None = None,
        parser: AlertParser | None = None,
    ):
        self.repository = repository
        self.email_client = email_client
        self.parser = parser

    async def execute_job(self, job: IngressJob) -> dict[str, Any]:
        """Executes a single ingress synchronization job for a household."""
        logger.info("Executing ingress job for household=%s user=%s", job.household_id, job.user_id)

        if job.status in ("needs_reconnect", "disconnected"):
            logger.info("Skipping household=%s in %s state", job.household_id, job.status)
            return {"success": False, "skipped": True, "reason": job.status}

        inserted_count = 0
        quarantined_count = 0
        skipped_count = 0

        try:
            # Resolve email client: use provided client or per-household client
            client = self.email_client
            if client is None:
                client = await GmailClient.for_household(household_id=job.household_id, repo=self.repository)

            if client is None:
                logger.warning(
                    "No Gmail credentials available for household=%s. Skipping job without error.",
                    job.household_id,
                )
                # Advance next_run_at with long backoff so due-job query does not busy-loop every 60s
                await self.repository.mark_job_status(
                    job_id=job.id,
                    status="idle",
                    interval_minutes=max(job.interval_minutes, 60),
                    error="No Gmail credentials configured",
                )
                return {"success": False, "skipped": True, "reason": "no_credentials"}

            checkpoint = await self.repository.get_checkpoint(job.household_id)
            after_date = checkpoint.last_email_internal_date if checkpoint else None

            messages = await client.fetch_alert_messages(
                query="label:INBOX",
                after_internal_date=after_date,
            )

            for msg in messages:
                raw_id = msg.get("id")
                internal_date = msg.get("internalDate")
                body = msg.get("text", "")

                email_url = client.build_email_url(raw_id)
                parsed = self.parser.parse(body, raw_email_id=raw_id) if self.parser else None

                if parsed is not None:
                    inserted = await self.repository.save_transaction(
                        household_id=job.household_id,
                        user_id=job.user_id,
                        alert=parsed,
                    )
                    if inserted:
                        inserted_count += 1
                    else:
                        skipped_count += 1

                    await self.repository.update_checkpoint(
                        household_id=job.household_id,
                        last_email_internal_date=internal_date,
                        increment_processed=1,
                    )
                else:
                    # Unrecognized alert format -> Quarantine
                    await self.repository.quarantine_email(
                        household_id=job.household_id,
                        user_id=job.user_id,
                        raw_email_id=raw_id,
                        email_url=email_url,
                        email_text=body,
                        error_reason="Unrecognized alert pattern",
                    )
                    quarantined_count += 1

            await self.repository.mark_job_status(
                job_id=job.id,
                status="idle",
                interval_minutes=job.interval_minutes,
                error=None,
            )

            return {
                "success": True,
                "inserted": inserted_count,
                "skipped": skipped_count,
                "quarantined": quarantined_count,
            }

        except Exception as e:
            if is_auth_error(e):
                readable_error = (
                    "Failed to decrypt stored credentials. Reconnection required."
                    if isinstance(e, OAuthDecryptionError)
                    else "Gmail access revoked or expired. Reconnection required."
                )
                logger.error(
                    "Auth failure for household=%s. Marking needs_reconnect: %s",
                    job.household_id,
                    readable_error,
                )
                await self.repository.mark_oauth_credential_invalid(
                    household_id=job.household_id,
                    source="gmail",
                )
                await self.repository.mark_job_status(
                    job_id=job.id,
                    status="needs_reconnect",
                    interval_minutes=job.interval_minutes,
                    error=readable_error,
                )
                return {
                    "success": False,
                    "error": readable_error,
                    "status": "needs_reconnect",
                }

            logger.error("Ingress job failed for household=%s: %s", job.household_id, e)
            await self.repository.mark_job_status(
                job_id=job.id,
                status="failed",
                interval_minutes=job.interval_minutes,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
                "inserted": inserted_count,
                "quarantined": quarantined_count,
            }
