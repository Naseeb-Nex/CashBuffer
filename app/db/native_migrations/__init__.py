"""Native PostgreSQL migration tool for CashBuffer using psycopg 3."""

from app.db.native_migrations.errors import (
    MigrationChecksumError,
    MigrationConnectionError,
    MigrationError,
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

__all__ = [
    "DEFAULT_MIGRATION_LOCK_ID",
    "MigrationChecksumError",
    "MigrationConnectionError",
    "MigrationError",
    "MigrationExecutionError",
    "MigrationFileError",
    "MigrationLockError",
    "MigrationRecord",
    "MigrationRunner",
    "MigrationFile",
    "PostgresAdvisoryLock",
    "compute_checksum",
    "load_migrations",
    "normalize_db_url",
]
