"""PostgreSQL advisory lock implementation for migration synchronization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

from app.db.native_migrations.errors import MigrationLockError

logger = logging.getLogger(__name__)

# Fixed 64-bit signed integer identifier for CashBuffer migration advisory lock
DEFAULT_MIGRATION_LOCK_ID: int = 8274910492837461


class PostgresAdvisoryLock:
    """Manages a PostgreSQL session-level advisory lock via psycopg 3."""

    def __init__(
        self,
        conn: psycopg.Connection,
        lock_id: int = DEFAULT_MIGRATION_LOCK_ID,
        blocking: bool = True,
        timeout_seconds: float | None = None,
    ) -> None:
        self.conn = conn
        self.lock_id = lock_id
        self.blocking = blocking
        self.timeout_seconds = timeout_seconds
        self._acquired = False

    def acquire(self) -> None:
        """Acquire the session-level advisory lock."""
        try:
            with self.conn.cursor() as cur:
                if not self.blocking:
                    cur.execute("SELECT pg_try_advisory_lock(%s);", (self.lock_id,))
                    row = cur.fetchone()
                    if not row or not row[0]:
                        raise MigrationLockError(
                            f"Migration advisory lock {self.lock_id} is already held by another process."
                        )
                else:
                    if self.timeout_seconds is not None:
                        timeout_ms = int(self.timeout_seconds * 1000)
                        cur.execute(f"SET LOCAL lock_timeout = '{timeout_ms}ms';")
                    cur.execute("SELECT pg_advisory_lock(%s);", (self.lock_id,))
            self._acquired = True
            logger.info("Acquired migration advisory lock %s", self.lock_id)
        except Exception as e:
            if isinstance(e, MigrationLockError):
                raise
            raise MigrationLockError(f"Failed to acquire advisory lock {self.lock_id}: {e}") from e

    def release(self) -> None:
        """Release the session-level advisory lock."""
        if not self._acquired:
            return

        try:
            # If the connection is closed, the lock was automatically released by Postgres
            if getattr(self.conn, "closed", False):
                self._acquired = False
                return

            # If connection is in an uncommitted/aborted transaction state, rollback first
            try:
                info = getattr(self.conn, "info", None)
                if info and hasattr(info, "transaction_status"):
                    import psycopg.pq

                    if info.transaction_status == psycopg.pq.TransactionStatus.ERROR:
                        self.conn.rollback()
            except Exception:
                pass

            with self.conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s);", (self.lock_id,))
            self._acquired = False
            logger.info("Released migration advisory lock %s", self.lock_id)
        except Exception as e:
            logger.warning("Error releasing migration advisory lock %s: %s", self.lock_id, e)
            self._acquired = False

    def __enter__(self) -> PostgresAdvisoryLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
