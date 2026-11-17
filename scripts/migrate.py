#!/usr/bin/env python3
"""CLI utility for running native PostgreSQL migrations."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.db.native_migrations.runner import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
