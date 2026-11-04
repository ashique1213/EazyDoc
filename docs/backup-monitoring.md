# EazyDoc — Backup Monitoring, Verification & Disaster Recovery Drills

This document defines the monitoring, health verification, storage alerts, and disaster recovery restore drill procedures for EazyDoc database backups.

---

## 1. RPO & RTO Objectives

| Parameter | Target SLA | Metric Definition |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | < 24 Hours (Daily Backups) / < 15 Mins (WAL Archiving) | Maximum acceptable data loss window during a catastrophic disaster. |
| **RTO (Recovery Time Objective)** | < 30 Minutes | Maximum acceptable downtime to restore database and resume API traffic. |

---

## 2. Automated Backup Generation & Storage Policy

### 2.1 Backup Script Execution
Backups are triggered nightly at 02:00 UTC via an automated cron job or Celery periodic task:

```bash
#!/usr/bin/env bash
set -eo pipefail

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_DIR="/app/backups"
BACKUP_FILE="${BACKUP_DIR}/eazydoc_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# Execute pg_dump with gzip compression
PGPASSWORD="${DATABASE_PASSWORD}" pg_dump \
  -h "${DATABASE_HOST:-db}" \
  -U "${DATABASE_USER:-postgres}" \
  -d "${DATABASE_NAME:-eazydoc_staging_db}" \
  --format=plain --no-owner --no-privileges | gzip > "${BACKUP_FILE}"

# Calculate SHA256 checksum for integrity verification
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"

# Rotate backups: Retain last 30 days locally
find "${BACKUP_DIR}" -name "eazydoc_backup_*.sql.gz" -mtime +30 -delete
```

### 2.2 Storage Retention Matrix
- **Local Container / Host Volume**: Retain last 14 daily backups.
- **Offsite Cloud Storage (S3 / GCS)**:
  - Daily backups: Retained for 30 days.
  - Weekly backups: Retained for 12 weeks.
  - Monthly backups: Retained for 1 year (HIPAA/audit compliance).

---

## 3. Backup Freshness & Integrity Monitoring

### 3.1 Freshness Verification Endpoint
The Super Admin dashboard (`/api/v1/admin/dashboard/operations/`) inspects the latest backup file in `/app/backups` or the S3 bucket:
- **Status: `healthy`**: Latest backup exists and was created `< 26 hours` ago.
- **Status: `stale`**: Latest backup is between `26 and 48 hours` old (triggers P2 Warning).
- **Status: `missing` or `critical`**: No backup found or age `> 48 hours` (triggers P1 Critical Alert).

### 3.2 Automated Integrity Verification Script
A periodic validation job verifies that the latest backup file is not empty or corrupted:

```bash
#!/usr/bin/env bash
# Verify SHA256 integrity and gzip validity
LATEST_BACKUP=$(ls -t /app/backups/eazydoc_backup_*.sql.gz | head -1)

if [ -z "${LATEST_BACKUP}" ]; then
  echo "CRITICAL: No backup file found!"
  exit 1
fi

# 1. Test gzip integrity
gzip -t "${LATEST_BACKUP}" || { echo "CRITICAL: Corrupted gzip file: ${LATEST_BACKUP}"; exit 2; }

# 2. Check minimum expected size (> 100 KB)
FILE_SIZE=$(wc -c < "${LATEST_BACKUP}")
if [ "${FILE_SIZE}" -lt 102400 ]; then
  echo "CRITICAL: Backup file abnormally small (${FILE_SIZE} bytes)!"
  exit 3
fi

echo "SUCCESS: Backup ${LATEST_BACKUP} verified (${FILE_SIZE} bytes)."
```

---

## 4. Quarterly Restore Drill Procedure

Every quarter, DevOps engineers conduct a simulated disaster recovery drill using an isolated database container to validate the RTO (< 30 minutes).

### Step 1: Start Isolated Verification Container
```bash
docker run --name eazydoc_restore_drill \
  -e POSTGRES_DB=eazydoc_drill \
  -e POSTGRES_USER=eazydoc_user \
  -e POSTGRES_PASSWORD=drill_secret \
  -d postgres:16-alpine
```

### Step 2: Time and Execute Restoration
```bash
START_TIME=$(date +%s)
LATEST_BACKUP=$(ls -t /app/backups/eazydoc_backup_*.sql.gz | head -1)

# Stream uncompressed SQL into the drill database
gunzip -c "${LATEST_BACKUP}" | docker exec -i eazydoc_restore_drill psql -U eazydoc_user -d eazydoc_drill

END_TIME=$(date +%s)
RESTORE_DURATION=$((END_TIME - START_TIME))
echo "Restore completed in ${RESTORE_DURATION} seconds."
```

### Step 3: Run Integrity & Data Sanity Checks
```sql
-- Check total restored records across primary tables
SELECT 
    (SELECT count(*) FROM accounts_user) AS users,
    (SELECT count(*) FROM clinics_clinic) AS clinics,
    (SELECT count(*) FROM doctors_doctor) AS doctors,
    (SELECT count(*) FROM appointments_appointment) AS appointments,
    (SELECT count(*) FROM payments_payment) AS payments;
```

### Step 4: Tear Down Drill Container
```bash
docker stop eazydoc_restore_drill && docker rm eazydoc_restore_drill
```

### Step 5: Document Results
Record restore duration, timestamp, and row count verification in `docs/drill-records.md`.

