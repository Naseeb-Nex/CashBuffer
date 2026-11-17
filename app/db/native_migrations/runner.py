"""PostgreSQL migration runner implemented with psycopg 3."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from app.db.native_migrations.errors import (
    MigrationChecksumError,
    MigrationConnectionError,
    MigrationError,
    MigrationExecutionError,
    MigrationFileError,
)
from app.db.native_migrations.lock import (
    DEFAULT_MIGRATION_LOCK_ID,
    PostgresAdvisoryLock,
)
from app.db.native_migrations.migration import (
    MigrationFile,
    load_migrations,
)

logger = logging.getLogger(__name__)

CREATE_SCHEMA_MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER NOT NULL DEFAULT 0
);
"""


@dataclass(frozen=True)
class MigrationRecord:
    """Record of an applied migration from schema_migrations table."""

    version: str
    name: str
    checksum: str
    applied_at: datetime
    execution_time_ms: int


def normalize_db_url(db_url: str) -> str:
    """Normalize SQLAlchemy or common PostgreSQL connection URLs to psycopg-compatible string."""
    url = db_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    elif url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://") :]
    elif url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


class MigrationRunner:
    """Executes numbered SQL migrations sequentially with advisory locks and checksum validation."""

    def __init__(
        self,
        db_url: str | None = None,
        migrations_dir: str | Path | None = None,
        lock_id: int = DEFAULT_MIGRATION_LOCK_ID,
    ) -> None:
        self.raw_db_url = db_url or os.getenv("DATABASE_URL")
        self.db_url = normalize_db_url(self.raw_db_url) if self.raw_db_url else None

        if migrations_dir is not None:
            self.migrations_dir = Path(migrations_dir)
        else:
            # Default to repo root migrations/ directory
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.migrations_dir = repo_root / "migrations"

        self.lock_id = lock_id

    def connect(self) -> psycopg.Connection:
        """Establish a new psycopg 3 connection to the database."""
        if not self.db_url:
            raise MigrationConnectionError(
                "No database URL provided. Set DATABASE_URL environment variable or pass db_url."
            )
        try:
            return psycopg.connect(self.db_url)
        except Exception as e:
            raise MigrationConnectionError(f"Failed to connect to database: {e}") from e

    def ensure_schema_migrations_table(self, conn: psycopg.Connection) -> None:
        """Ensure the schema_migrations tracking table exists."""
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(CREATE_SCHEMA_MIGRATIONS_TABLE_SQL)
        except Exception as e:
            raise MigrationExecutionError(f"Failed to create schema_migrations table: {e}") from e

    def get_applied_migrations(self, conn: psycopg.Connection) -> dict[str, MigrationRecord]:
        """Fetch all previously applied migrations from schema_migrations."""
        self.ensure_schema_migrations_table(conn)
        applied: dict[str, MigrationRecord] = {}
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT version, name, checksum, applied_at, execution_time_ms
                    FROM schema_migrations
                    ORDER BY version ASC;
                    """
                )
                for row in cur.fetchall():
                    rec = MigrationRecord(
                        version=str(row[0]),
                        name=str(row[1]),
                        checksum=str(row[2]),
                        applied_at=row[3],
                        execution_time_ms=int(row[4]) if row[4] is not None else 0,
                    )
                    applied[rec.version] = rec
        except Exception as e:
            raise MigrationExecutionError(f"Failed to query schema_migrations: {e}") from e

        return applied

    def validate_checksums(
        self,
        applied: dict[str, MigrationRecord],
        local_files: list[MigrationFile],
    ) -> None:
        """Verify that applied migrations on record match local file contents."""
        local_map = {m.version_str: m for m in local_files}

        for version, record in applied.items():
            local = local_map.get(version)
            if local is None:
                raise MigrationFileError(
                    f"Applied migration version {version} ('{record.name}') is missing from migrations directory."
                )
            if local.checksum != record.checksum:
                raise MigrationChecksumError(
                    f"Checksum mismatch for migration {version} ('{local.filename}'): "
                    f"recorded={record.checksum}, current={local.checksum}. "
                    f"Applied migrations must not be modified."
                )

    def run_migrations(
        self,
        conn: psycopg.Connection | None = None,
        target_version: int | None = None,
        dry_run: bool = False,
        blocking_lock: bool = True,
        lock_timeout_seconds: float | None = None,
    ) -> list[MigrationRecord]:
        """Run pending migrations inside transactional advisory lock.

        Returns list of newly applied MigrationRecords.
        """
        managed_conn = False
        if conn is None:
            conn = self.connect()
            managed_conn = True

        try:
            with PostgresAdvisoryLock(
                conn,
                lock_id=self.lock_id,
                blocking=blocking_lock,
                timeout_seconds=lock_timeout_seconds,
            ):
                self.ensure_schema_migrations_table(conn)
                local_migrations = load_migrations(self.migrations_dir)
                applied = self.get_applied_migrations(conn)

                # Checksum validation on all previously applied migrations
                self.validate_checksums(applied, local_migrations)

                pending: list[MigrationFile] = [
                    m for m in local_migrations if m.version_str not in applied
                ]

                if target_version is not None:
                    pending = [m for m in pending if m.version_num <= target_version]

                if not pending:
                    logger.info("No pending migrations to apply.")
                    return []

                newly_applied: list[MigrationRecord] = []

                for migration in pending:
                    logger.info("Applying migration %s: %s", migration.version_str, migration.name)
                    if dry_run:
                        logger.info("[DRY RUN] Would apply migration %s", migration.filename)
                        newly_applied.append(
                            MigrationRecord(
                                version=migration.version_str,
                                name=migration.name,
                                checksum=migration.checksum,
                                applied_at=datetime.now(),
                                execution_time_ms=0,
                            )
                        )
                        continue

                    start = time.perf_counter()
                    try:
                        with conn.transaction():
                            with conn.cursor() as cur:
                                cur.execute(migration.content)
                                duration_ms = max(1, int((time.perf_counter() - start) * 1000))
                                cur.execute(
                                    """
                                    INSERT INTO schema_migrations (version, name, checksum, applied_at, execution_time_ms)
                                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
                                    RETURNING applied_at;
                                    """,
                                    (
                                        migration.version_str,
                                        migration.name,
                                        migration.checksum,
                                        duration_ms,
                                    ),
                                )
                                row = cur.fetchone()
                                applied_at = row[0] if row else datetime.now()

                                newly_applied.append(
                                    MigrationRecord(
                                        version=migration.version_str,
                                        name=migration.name,
                                        checksum=migration.checksum,
                                        applied_at=applied_at,
                                        execution_time_ms=duration_ms,
                                    )
                                )
                        logger.info(
                            "Applied migration %s (%s ms)", migration.version_str, duration_ms
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to apply migration %s ('%s'): %s",
                            migration.version_str,
                            migration.filename,
                            e,
                        )
                        raise MigrationExecutionError(
                            f"Migration {migration.filename} failed: {e}"
                        ) from e

                return newly_applied
        finally:
            if managed_conn and not conn.closed:
                conn.close()

    def get_status(self, conn: psycopg.Connection | None = None) -> list[dict[str, Any]]:
        """Return the status of all discovered migrations (applied vs pending)."""
        managed_conn = False
        if conn is None:
            conn = self.connect()
            managed_conn = True

        try:
            self.ensure_schema_migrations_table(conn)
            local_migrations = load_migrations(self.migrations_dir)
            applied = self.get_applied_migrations(conn)

            status_list: list[dict[str, Any]] = []
            for m in local_migrations:
                is_applied = m.version_str in applied
                rec = applied.get(m.version_str)
                status_list.append(
                    {
                        "version": m.version_str,
                        "name": m.name,
                        "filename": m.filename,
                        "status": "applied" if is_applied else "pending",
                        "checksum": m.checksum,
                        "applied_checksum": rec.checksum if rec else None,
                        "checksum_match": (rec.checksum == m.checksum) if rec else None,
                        "applied_at": rec.applied_at.isoformat() if rec else None,
                        "execution_time_ms": rec.execution_time_ms if rec else None,
                    }
                )
            return status_list
        finally:
            if managed_conn and not conn.closed:
                conn.close()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for running PostgreSQL native migrations."""
    parser = argparse.ArgumentParser(description="CashBuffer native PostgreSQL migration runner")
    parser.add_argument("--db-url", help="Database connection URL (defaults to DATABASE_URL)")
    parser.add_argument(
        "--migrations-dir", help="Directory containing numbered .sql migration files"
    )
    parser.add_argument("--status", action="store_true", help="Display migration status table")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migrations without applying")
    parser.add_argument(
        "--target", type=int, help="Target migration version to migrate up to (inclusive)"
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    runner = MigrationRunner(db_url=args.db_url, migrations_dir=args.migrations_dir)

    try:
        if args.status:
            statuses = runner.get_status()
            print("\nMigration Status:")
            print(f"{'Version':<8} {'Status':<10} {'Name':<30} {'Applied At':<25}")
            print("-" * 75)
            for s in statuses:
                applied_str = s["applied_at"] or "-"
                print(f"{s['version']:<8} {s['status']:<10} {s['name']:<30} {applied_str:<25}")
            print()
            return 0

        applied = runner.run_migrations(target_version=args.target, dry_run=args.dry_run)
        if applied:
            print(f"\nSuccessfully processed {len(applied)} migration(s):")
            for m in applied:
                print(f"  - [{m.version}] {m.name} ({m.execution_time_ms} ms)")
        else:
            print("\nDatabase is already up to date. No migrations to apply.")
        return 0

    except MigrationError as e:
        logger.error("Migration error: %s", e)
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error during migrations: %s", e)
        print(f"\nUNEXPECTED ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
