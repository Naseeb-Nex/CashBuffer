"""Migration file representations and checksum utilities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.db.native_migrations.errors import MigrationFileError

MIGRATION_FILE_PATTERN = re.compile(r"^(\d+)_([a-zA-Z0-9_\-]+)\.sql$")


def compute_checksum(content: str) -> str:
    """Compute deterministic SHA-256 checksum of SQL content with normalized line breaks."""
    normalized = content.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MigrationFile:
    """Represents a discovered SQL migration file."""

    version_num: int
    version_str: str
    name: str
    filename: str
    path: Path
    content: str
    checksum: str


def load_migrations(migrations_dir: str | Path) -> list[MigrationFile]:
    """Discover, parse, and validate SQL migration files in numeric sequence."""
    path = Path(migrations_dir)
    if not path.exists():
        raise MigrationFileError(f"Migrations directory does not exist: {path}")
    if not path.is_dir():
        raise MigrationFileError(f"Migrations path is not a directory: {path}")

    migrations: list[MigrationFile] = []
    seen_versions: dict[int, str] = {}

    for file_path in path.iterdir():
        if not file_path.is_file() or not file_path.name.endswith(".sql"):
            continue

        match = MIGRATION_FILE_PATTERN.match(file_path.name)
        if not match:
            # Skip non-conforming SQL files or raise? Skipping non-matching files is fine, but log if needed
            continue

        version_str, name = match.groups()
        version_num = int(version_str)

        if version_num in seen_versions:
            raise MigrationFileError(
                f"Duplicate migration version {version_num}: "
                f"'{seen_versions[version_num]}' and '{file_path.name}'"
            )

        content = file_path.read_text(encoding="utf-8")
        checksum = compute_checksum(content)

        migrations.append(
            MigrationFile(
                version_num=version_num,
                version_str=version_str,
                name=name,
                filename=file_path.name,
                path=file_path,
                content=content,
                checksum=checksum,
            )
        )
        seen_versions[version_num] = file_path.name

    migrations.sort(key=lambda m: m.version_num)
    return migrations
