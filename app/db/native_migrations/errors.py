"""Exceptions for native PostgreSQL migration runner."""


class MigrationError(Exception):
    """Base exception for all native migration errors."""

    pass


class MigrationLockError(MigrationError):
    """Raised when acquiring or releasing Postgres advisory lock fails."""

    pass


class MigrationChecksumError(MigrationError):
    """Raised when recorded checksum differs from local migration file."""

    pass


class MigrationFileError(MigrationError):
    """Raised when migration files are invalid, missing, or duplicate."""

    pass


class MigrationExecutionError(MigrationError):
    """Raised when a migration fails to execute."""

    pass


class MigrationConnectionError(MigrationError):
    """Raised when database connection cannot be established."""

    pass
