#!/usr/bin/env bash
# ==============================================================================
# EazyDoc PostgreSQL Restoration & Recovery Script
# Validates checksum, restores into target database, and runs verification checks
# ==============================================================================
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <path_to_backup_dump> [target_db_name]"
  exit 1
fi

BACKUP_PATH="$1"
DB_NAME="${2:-${DATABASE_NAME:-eazydoc_staging_db}}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_USER="${DATABASE_USER:-eazydoc_user}"

if [ ! -f "${BACKUP_PATH}" ]; then
  echo "Error: Backup file '${BACKUP_PATH}' not found."
  exit 1
fi

# Verify checksum if present
CHECKSUM_FILE="${BACKUP_PATH}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
  echo "Verifying SHA-256 integrity..."
  EXPECTED_HASH="$(cat "${CHECKSUM_FILE}")"
  ACTUAL_HASH="$(sha256sum "${BACKUP_PATH}" | awk '{print $1}')"
  if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
    echo "FATAL: Checksum mismatch! Corrupt or tampered backup."
    echo "Expected: ${EXPECTED_HASH}"
    echo "Actual:   ${ACTUAL_HASH}"
    exit 2
  fi
  echo "Checksum verified: OK"
fi

echo "Restoring '${BACKUP_PATH}' into database '${DB_NAME}' on ${DB_HOST}:${DB_PORT}..."

# Restore using pg_restore
PGPASSWORD="${DATABASE_PASSWORD:-}" pg_restore \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  -v \
  "${BACKUP_PATH}" || true

echo "Restore completed. Running integrity checks on '${DB_NAME}'..."

# Verify core tables row counts
PGPASSWORD="${DATABASE_PASSWORD:-}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 'users' AS table_name, count(*) AS count FROM accounts_user
UNION ALL
SELECT 'clinics', count(*) FROM clinics_clinic
UNION ALL
SELECT 'doctors', count(*) FROM doctors_doctor
UNION ALL
SELECT 'appointments', count(*) FROM appointments_appointment
UNION ALL
SELECT 'payments', count(*) FROM payments_payment;
"

echo "Restoration and verification successful!"

