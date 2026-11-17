"""Focused tests for native PostgreSQL migration runner and Phase 1 migrations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest

from app.db.native_migrations.errors import (
    MigrationChecksumError,
    MigrationConnectionError,
    MigrationExecutionError,
    MigrationFileError,
    MigrationLockError,
)
from app.db.native_migrations.lock import (
    DEFAULT_MIGRATION_LOCK_ID,
    PostgresAdvisoryLock,
)
from app.db.native_migrations.migration import (
    MigrationFile,
    compute_checksum,
    load_migrations,
)
from app.db.native_migrations.runner import (
    MigrationRecord,
    MigrationRunner,
    normalize_db_url,
)


def test_normalize_db_url():
    """Verify various Postgres URL schemes normalize to standard psycopg postgresql:// format."""
    assert (
        normalize_db_url("postgresql+asyncpg://user:pass@localhost:5432/dbname")
        == "postgresql://user:pass@localhost:5432/dbname"
    )
    assert (
        normalize_db_url("postgresql+psycopg://user:pass@localhost:5432/dbname")
        == "postgresql://user:pass@localhost:5432/dbname"
    )
    assert (
        normalize_db_url("postgres://user:pass@localhost:5432/dbname")
        == "postgresql://user:pass@localhost:5432/dbname"
    )
    assert (
        normalize_db_url("postgresql://user:pass@localhost:5432/dbname")
        == "postgresql://user:pass@localhost:5432/dbname"
    )


def test_compute_checksum_normalization():
    """Verify that CRLF vs LF line endings and surrounding whitespace produce identical checksums."""
    text_unix = "CREATE TABLE test (\n  id SERIAL PRIMARY KEY\n);\n"
    text_windows = "CREATE TABLE test (\r\n  id SERIAL PRIMARY KEY\r\n);\r\n"
    text_padded = "\n\n  CREATE TABLE test (\n  id SERIAL PRIMARY KEY\n);  \n"

    assert compute_checksum(text_unix) == compute_checksum(text_windows)
    assert compute_checksum(text_unix) == compute_checksum(text_padded)
    assert len(compute_checksum(text_unix)) == 64


def test_load_migrations_order_and_metadata():
    """Verify existing numbered migrations directory loads in strict sequential order."""
    repo_root = Path(__file__).resolve().parent.parent
    migrations_dir = repo_root / "migrations"

    migrations = load_migrations(migrations_dir)
    assert len(migrations) >= 4

    versions = [m.version_num for m in migrations]
    assert versions == sorted(versions)
    assert versions[:4] == [1, 2, 3, 4]

    names = [m.name for m in migrations]
    assert names[0] == "baseline_identity"
    assert names[1] == "household"
    assert names[2] == "core_ledger"
    assert names[3] == "ingress"

    for m in migrations:
        assert m.checksum == compute_checksum(m.content)
        assert len(m.content) > 0


def test_load_migrations_duplicate_version_fails(tmp_path: Path):
    """Verify that having two migration files with the same version number raises MigrationFileError."""
    (tmp_path / "001_initial.sql").write_text("SELECT 1;")
    (tmp_path / "001_conflicting.sql").write_text("SELECT 2;")

    with pytest.raises(MigrationFileError, match="Duplicate migration version 1"):
        load_migrations(tmp_path)


def test_load_migrations_missing_dir():
    """Verify that a non-existent migrations directory raises MigrationFileError."""
    with pytest.raises(MigrationFileError, match="does not exist"):
        load_migrations(Path("/non/existent/path/for/migrations"))


def test_migration_sql_baseline_identity_spec():
    """Verify 001_baseline_identity.sql preserves Kinde subject in idp_user_id while users.id is UUID."""
    repo_root = Path(__file__).resolve().parent.parent
    migration_file = repo_root / "migrations" / "001_baseline_identity.sql"
    sql = migration_file.read_text(encoding="utf-8")

    assert "id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in sql
    assert "idp_user_id VARCHAR(255) NOT NULL" in sql
    assert "uq_users_idp_user_id UNIQUE (idp_user_id)" in sql
    assert "idx_users_idp_user_id ON users (idp_user_id)" in sql


def test_migration_sql_household_and_ingress_spec():
    """Verify household, core ledger, and ingress migrations define appropriate tables and constraints."""
    repo_root = Path(__file__).resolve().parent.parent
    household_sql = (repo_root / "migrations" / "002_household.sql").read_text(encoding="utf-8")
    ledger_sql = (repo_root / "migrations" / "003_core_ledger.sql").read_text(encoding="utf-8")
    ingress_sql = (repo_root / "migrations" / "004_ingress.sql").read_text(encoding="utf-8")

    # Household tables
    assert "CREATE TABLE IF NOT EXISTS households" in household_sql
    assert "CREATE TABLE IF NOT EXISTS household_members" in household_sql
    assert "PRIMARY KEY (household_id, user_id)" in household_sql

    # Core ledger tables
    assert "CREATE TABLE IF NOT EXISTS categories" in ledger_sql
    assert "CREATE TABLE IF NOT EXISTS vendor_rules" in ledger_sql
    assert "CREATE TABLE IF NOT EXISTS transactions" in ledger_sql
    assert "CREATE TABLE IF NOT EXISTS llm_configs" in ledger_sql

    # Ingress tables
    assert "CREATE TABLE IF NOT EXISTS oauth_credentials" in ingress_sql
    assert "CREATE TABLE IF NOT EXISTS ingress_sources" in ingress_sql
    assert "CREATE TABLE IF NOT EXISTS ingress_payloads" in ingress_sql
    assert "CREATE TABLE IF NOT EXISTS quarantined_emails" in ingress_sql


def test_advisory_lock_blocking():
    """Verify PostgresAdvisoryLock acquires and releases session-level lock."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.closed = False

    lock = PostgresAdvisoryLock(mock_conn, lock_id=DEFAULT_MIGRATION_LOCK_ID)
    with lock:
        mock_cursor.execute.assert_called_with("SELECT pg_advisory_lock(%s);", (DEFAULT_MIGRATION_LOCK_ID,))

    mock_cursor.execute.assert_called_with("SELECT pg_advisory_unlock(%s);", (DEFAULT_MIGRATION_LOCK_ID,))


def test_advisory_lock_non_blocking_conflict():
    """Verify PostgresAdvisoryLock raises MigrationLockError if non-blocking lock cannot be acquired."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (False,)  # lock acquisition failed
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.closed = False

    lock = PostgresAdvisoryLock(mock_conn, lock_id=DEFAULT_MIGRATION_LOCK_ID, blocking=False)
    with pytest.raises(MigrationLockError, match="already held by another process"):
        with lock:
            pass


def test_validate_checksums_success():
    """Verify validate_checksums passes when checksums match."""
    runner = MigrationRunner(db_url="postgresql://user:pass@localhost/db")

    local = [
        MigrationFile(
            version_num=1,
            version_str="001",
            name="test",
            filename="001_test.sql",
            path=Path("001_test.sql"),
            content="SELECT 1;",
            checksum="abc12345",
        )
    ]
    applied = {
        "001": MigrationRecord(
            version="001",
            name="test",
            checksum="abc12345",
            applied_at=datetime.now(),
            execution_time_ms=10,
        )
    }

    # Should not raise
    runner.validate_checksums(applied, local)


def test_validate_checksums_mismatch():
    """Verify validate_checksums raises MigrationChecksumError when an applied migration was altered."""
    runner = MigrationRunner(db_url="postgresql://user:pass@localhost/db")

    local = [
        MigrationFile(
            version_num=1,
            version_str="001",
            name="test",
            filename="001_test.sql",
            path=Path("001_test.sql"),
            content="SELECT 1; -- altered",
            checksum="different_checksum",
        )
    ]
    applied = {
        "001": MigrationRecord(
            version="001",
            name="test",
            checksum="recorded_checksum",
            applied_at=datetime.now(),
            execution_time_ms=10,
        )
    }

    with pytest.raises(MigrationChecksumError, match="Checksum mismatch for migration 001"):
        runner.validate_checksums(applied, local)


def test_validate_checksums_missing_file():
    """Verify validate_checksums raises MigrationFileError when an applied migration file is deleted."""
    runner = MigrationRunner(db_url="postgresql://user:pass@localhost/db")

    local = []
    applied = {
        "001": MigrationRecord(
            version="001",
            name="deleted",
            checksum="recorded_checksum",
            applied_at=datetime.now(),
            execution_time_ms=10,
        )
    }

    with pytest.raises(MigrationFileError, match="missing from migrations directory"):
        runner.validate_checksums(applied, local)


def test_runner_run_migrations_lifecycle(tmp_path: Path):
    """Verify full migration execution lifecycle: lock, schema_migrations table, run, record."""
    (tmp_path / "001_first.sql").write_text("CREATE TABLE t1 (id int);")
    (tmp_path / "002_second.sql").write_text("CREATE TABLE t2 (id int);")

    mock_cursor = MagicMock()
    # First fetchall for get_applied_migrations -> empty (no migrations applied yet)
    mock_cursor.fetchall.return_value = []
    # fetchone for RETURNING applied_at
    mock_cursor.fetchone.return_value = (datetime(2026, 1, 1, 12, 0, 0),)

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.transaction.return_value.__enter__.return_value = None

    runner = MigrationRunner(migrations_dir=tmp_path)
    applied = runner.run_migrations(conn=mock_conn)

    assert len(applied) == 2
    assert applied[0].version == "001"
    assert applied[1].version == "002"

    # Verify SQL execution calls
    exec_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    # Advisory lock
    assert any("pg_advisory_lock" in str(c) for c in exec_calls)
    # Applied migration SQLs
    assert any("CREATE TABLE t1" in str(c) for c in exec_calls)
    assert any("CREATE TABLE t2" in str(c) for c in exec_calls)
    # Advisory unlock
    assert any("pg_advisory_unlock" in str(c) for c in exec_calls)


def test_runner_transaction_rollback_on_execution_error(tmp_path: Path):
    """Verify transaction rolls back and MigrationExecutionError is raised when migration SQL fails."""
    (tmp_path / "001_bad.sql").write_text("SYNTAX ERROR;")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    # Make executing the migration SQL fail
    def execute_side_effect(sql, *args, **kwargs):
        if "SYNTAX ERROR" in sql:
            raise psycopg.ProgrammingError("syntax error at or near 'SYNTAX'")
        return None

    mock_cursor.execute.side_effect = execute_side_effect

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    runner = MigrationRunner(migrations_dir=tmp_path)

    with pytest.raises(MigrationExecutionError, match="Migration 001_bad.sql failed"):
        runner.run_migrations(conn=mock_conn)

    # Advisory unlock must still be executed to release lock
    assert any("pg_advisory_unlock" in str(c[0][0]) for c in mock_cursor.execute.call_args_list)


def test_runner_dry_run_does_not_modify(tmp_path: Path):
    """Verify dry_run identifies pending migrations without executing DDL."""
    (tmp_path / "001_first.sql").write_text("CREATE TABLE t1 (id int);")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    runner = MigrationRunner(migrations_dir=tmp_path)
    applied = runner.run_migrations(conn=mock_conn, dry_run=True)

    assert len(applied) == 1
    assert applied[0].version == "001"

    exec_calls = [c[0][0] for c in mock_cursor.execute.call_args_list]
    assert not any("CREATE TABLE t1" in str(c) for c in exec_calls)


def test_runner_status_reporting(tmp_path: Path):
    """Verify get_status returns accurate status dictionaries."""
    (tmp_path / "001_first.sql").write_text("SELECT 1;")
    (tmp_path / "002_second.sql").write_text("SELECT 2;")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("001", "first", compute_checksum("SELECT 1;"), datetime(2026, 1, 1), 12),
    ]

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    runner = MigrationRunner(migrations_dir=tmp_path)
    status = runner.get_status(conn=mock_conn)

    assert len(status) == 2
    assert status[0]["version"] == "001"
    assert status[0]["status"] == "applied"
    assert status[0]["checksum_match"] is True

    assert status[1]["version"] == "002"
    assert status[1]["status"] == "pending"
    assert status[1]["checksum_match"] is None


def test_runner_missing_db_url_error():
    """Verify MigrationConnectionError is raised when trying to connect without a database URL."""
    runner = MigrationRunner(db_url=None)
    runner.db_url = None
    with pytest.raises(MigrationConnectionError, match="No database URL provided"):
        runner.connect()
