"""Ingress synchronization service orchestrating fetch -> parse -> dedupe -> insert."""

from __future__ import annotations

import logging
from typing import Any

from apps.ingress.src.domain.interfaces import AlertParser, EmailClient, IngressRepository
from apps.ingress.src.domain.models import IngressJob

logger = logging.getLogger(__name__)

class IngressSyncService:
    """Coordinates parsing, deduplication, transaction persistence, and error quarantine."""

    def __init__(
        self,
        repository: IngressRepository,
        email_client: EmailClient,
        parser: AlertParser,
    ):
        self.repository = repository
        self.email_client = email_client
        self.parser = parser

    async def execute_job(self, job: IngressJob) -> dict[str, Any]:
        """Executes a single ingress synchronization job for a household."""
        logger.info("Executing ingress job for household=%s user=%s", job.household_id, job.user_id)
        inserted_count = 0
        quarantined_count = 0
        skipped_count = 0

        try:
            checkpoint = await self.repository.get_checkpoint(job.household_id)
            after_date = checkpoint.last_email_internal_date if checkpoint else None

            messages = await self.email_client.fetch_alert_messages(
                query="label:INBOX",
                after_internal_date=after_date,
            )

            for msg in messages:
                raw_id = msg.get("id")
                internal_date = msg.get("internalDate")
                body = msg.get("text", "")

                email_url = self.email_client.build_email_url(raw_id)
                parsed = self.parser.parse(body, raw_email_id=raw_id)

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
