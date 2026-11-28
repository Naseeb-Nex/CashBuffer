"""Pure psycopg 3 repository for Ingress microservice."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from psycopg.rows import dict_row

from apps.ingress.src.domain.interfaces import IngressRepository
from apps.ingress.src.domain.models import (
    IngressJob,
    OAuthCredential,
    ParsedAlert,
    SyncCheckpoint,
)

logger = logging.getLogger(__name__)

class NativeIngressRepository(IngressRepository):
    """psycopg 3 parameterized repository with zero ORM overhead."""

    def __init__(self, pool: Any):
        self.pool = pool

    async def fetch_due_jobs(self) -> list[IngressJob]:
        query = """
            SELECT id, household_id, user_id, provider, interval_minutes, next_run_at, status
            FROM ingress_configs
            WHERE is_enabled = TRUE
              AND next_run_at <= CURRENT_TIMESTAMP
              AND status NOT IN ('running', 'needs_reconnect', 'disconnected')
            ORDER BY next_run_at ASC;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                jobs: list[IngressJob] = []
                for r in rows:
                    jobs.append(
                        IngressJob(
                            id=uuid.UUID(str(r["id"])),
                            household_id=uuid.UUID(str(r["household_id"])),
                            user_id=uuid.UUID(str(r["user_id"])),
                            provider=r["provider"],
                            interval_minutes=int(r["interval_minutes"]),
                            next_run_at=r["next_run_at"],
                            status=r["status"],
                        )
                    )
                return jobs

    async def save_transaction(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        alert: ParsedAlert,
    ) -> bool:
        dedupe_hash = alert.compute_dedupe_hash(household_id)
        insert_sql = """
            INSERT INTO transactions (
                user_id, household_id, amount, currency, is_inflow,
                record_date, vendor_raw, tx_hash, dedupe_hash, status,
                raw_source, raw_email_id, email_url, created_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (dedupe_hash) DO NOTHING
            RETURNING id;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    insert_sql,
                    (
                        user_id,
                        household_id,
                        alert.amount,
                        alert.currency,
                        alert.is_inflow,
                        alert.record_date,
                        alert.vendor_raw,
                        dedupe_hash,  # tx_hash
                        dedupe_hash,  # dedupe_hash
                        alert.status,
                        alert.raw_source,
                        alert.raw_email_id,
                        alert.email_url,
                    ),
                )
                row = await cur.fetchone()
                return row is not None

    async def quarantine_email(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        raw_email_id: str | None,
        email_url: str | None,
        email_text: str,
        error_reason: str,
    ) -> None:
        query = """
            INSERT INTO quarantined_emails (
                household_id, user_id, raw_email_id, email_url, email_text, error_reason, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (household_id, user_id, raw_email_id, email_url, email_text, error_reason),
                )

    async def get_checkpoint(self, household_id: uuid.UUID) -> SyncCheckpoint | None:
        query = """
            SELECT household_id, last_history_id, last_email_internal_date, total_processed, updated_at
            FROM ingress_sync_state
            WHERE household_id = %s;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (household_id,))
                row = await cur.fetchone()
                if not row:
                    return None
                return SyncCheckpoint(
                    household_id=uuid.UUID(str(row["household_id"])),
                    last_history_id=row.get("last_history_id"),
                    last_email_internal_date=row.get("last_email_internal_date"),
                    total_processed=row.get("total_processed", 0),
                    updated_at=row.get("updated_at"),
                )

    async def update_checkpoint(
        self,
        household_id: uuid.UUID,
        last_email_internal_date: int | None,
        increment_processed: int = 1,
    ) -> None:
        query = """
            INSERT INTO ingress_sync_state (
                household_id, last_email_internal_date, total_processed, updated_at
            )
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (household_id) DO UPDATE SET
                last_email_internal_date = GREATEST(COALESCE(ingress_sync_state.last_email_internal_date, 0), EXCLUDED.last_email_internal_date),
                total_processed = ingress_sync_state.total_processed + EXCLUDED.total_processed,
                updated_at = CURRENT_TIMESTAMP;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (household_id, last_email_internal_date, increment_processed),
                )

    async def mark_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
        interval_minutes: int,
        error: str | None = None,
    ) -> None:
        query = """
            UPDATE ingress_configs
            SET status = %s,
                last_run_at = CURRENT_TIMESTAMP,
                next_run_at = CURRENT_TIMESTAMP + (%s || ' minutes')::interval,
                last_error = %s
            WHERE id = %s;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (status, interval_minutes, error, job_id))

    async def get_oauth_credential(
        self,
        household_id: uuid.UUID,
        source: str = "gmail",
    ) -> OAuthCredential | None:
        query = """
            SELECT id, user_id, household_id, source, encrypted_access_token,
                   encrypted_refresh_token, expires_at, is_valid, account_email,
                   scopes, created_at, updated_at
            FROM oauth_credentials
            WHERE household_id = %s AND source = %s AND is_valid = TRUE
            ORDER BY updated_at DESC
            LIMIT 1;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (household_id, source))
                row = await cur.fetchone()
                if not row:
                    return None
                return OAuthCredential(
                    id=row["id"],
                    user_id=uuid.UUID(str(row["user_id"])),
                    household_id=uuid.UUID(str(row["household_id"])) if row.get("household_id") else None,
                    source=row["source"],
                    encrypted_access_token=row["encrypted_access_token"],
                    encrypted_refresh_token=row["encrypted_refresh_token"],
                    expires_at=row["expires_at"],
                    is_valid=row["is_valid"],
                    account_email=row.get("account_email"),
                    scopes=row.get("scopes"),
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at"),
                )

    async def update_oauth_credential(
        self,
        credential_id: int,
        encrypted_access_token: str,
        expires_at: Any,
        encrypted_refresh_token: str | None = None,
    ) -> None:
        if encrypted_refresh_token:
            query = """
                UPDATE oauth_credentials
                SET encrypted_access_token = %s,
                    encrypted_refresh_token = %s,
                    expires_at = %s,
                    is_valid = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """
            params = (encrypted_access_token, encrypted_refresh_token, expires_at, credential_id)
        else:
            query = """
                UPDATE oauth_credentials
                SET encrypted_access_token = %s,
                    expires_at = %s,
                    is_valid = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """
            params = (encrypted_access_token, expires_at, credential_id)

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)

    async def mark_oauth_credential_invalid(
        self,
        credential_id: int | None = None,
        household_id: uuid.UUID | None = None,
        source: str = "gmail",
    ) -> None:
        if credential_id is not None:
            query = "UPDATE oauth_credentials SET is_valid = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s;"
            params = (credential_id,)
        elif household_id is not None:
            query = "UPDATE oauth_credentials SET is_valid = FALSE, updated_at = CURRENT_TIMESTAMP WHERE household_id = %s AND source = %s;"
            params = (household_id, source)
        else:
            return

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)

    async def update_ingress_config_status(
        self,
        household_id: uuid.UUID,
        status: str,
        error: str | None = None,
        provider: str = "gmail",
    ) -> None:
        query = """
            UPDATE ingress_configs
            SET status = %s,
                last_error = %s
            WHERE household_id = %s AND provider = %s;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (status, error, household_id, provider))

