#!/usr/bin/env bash
set -euo pipefail

# CashBuffer Automated PostgreSQL Backup Script
BACKUP_DIR="${BACKUP_DIR:-backups}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-cashbuffer}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_FILE="${BACKUP_DIR}/cashbuffer_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Backing up database '${POSTGRES_DB}' to '${TARGET_FILE}'..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${TARGET_FILE}"

echo "Backup created successfully: ${TARGET_FILE} ($(du -h "${TARGET_FILE}" | cut -f1))"
