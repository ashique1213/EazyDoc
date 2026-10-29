#!/usr/bin/env bash
# ==============================================================================
# EazyDoc PostgreSQL Production Backup Script
# Automated custom-format dump with compression, checksums, and rotation
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-eazydoc_db}"
DB_USER="${DATABASE_USER:-eazydoc_user}"

TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILENAME="${DB_NAME}_${TIMESTAMP}.dump"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
CHECKSUM_PATH="${BACKUP_PATH}.sha256"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting database backup for '${DB_NAME}'..."

# Execute pg_dump with custom compressed format
PGPASSWORD="${DATABASE_PASSWORD:-}" pg_dump \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  -F c \
  -Z 9 \
  -b \
  -v \
  -f "${BACKUP_PATH}"

# Generate SHA-256 checksum
sha256sum "${BACKUP_PATH}" | awk '{print $1}' > "${CHECKSUM_PATH}"

BACKUP_SIZE="$(du -h "${BACKUP_PATH}" | cut -f1)"
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Backup completed successfully."
echo "File: ${BACKUP_PATH} (${BACKUP_SIZE})"
echo "SHA-256: $(cat "${CHECKSUM_PATH}")"

# Prune local backups older than RETENTION_DAYS
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "${DB_NAME}_*.dump*" -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Backup routine finished."

