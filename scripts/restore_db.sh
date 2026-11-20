#!/usr/bin/env bash
set -euo pipefail

# CashBuffer Automated PostgreSQL Restore Script
if [ -z "${1:-}" ]; then
  echo "Usage: $0 <path_to_backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-cashbuffer}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Error: Backup file '${BACKUP_FILE}' not found."
  exit 1
fi

echo "Restoring '${BACKUP_FILE}' into '${POSTGRES_DB}'..."
gunzip -c "${BACKUP_FILE}" | docker compose exec -T db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

echo "Database restored successfully from ${BACKUP_FILE}."
