# EazyDoc — Production Disaster Recovery & Backup Plan

This document establishes the verified disaster recovery strategy, automated backup schedules, recovery objectives, and step-by-step restoration procedures for the EazyDoc production infrastructure.

---

## 1. Disaster Recovery Objectives (Proposed Targets for Approval)

> [!IMPORTANT]
> The following RPO and RTO targets are engineering baselines proposed for executive and stakeholder sign-off:

| Metric | Proposed Baseline | Approval Status | Technical Mechanism |
| :--- | :--- | :---: | :--- |
| **Recovery Point Objective (RPO)** | **$\le$ 15 Minutes** (with WAL Archiving)<br>**$\le$ 24 Hours** (Daily Backups) | *Pending Executive Approval* | Continuous PostgreSQL WAL archiving + Nightly automated `pg_dump` |
| **Recovery Time Objective (RTO)** | **$\le$ 30 Minutes** | *Pending Executive Approval* | Automated containerized restore script with SHA-256 verification |
| **Target Availability (SLA)** | **99.9% Uptime** (~43 mins downtime/month) | *Pending Executive Approval* | Multi-container Docker Compose with auto-restart policies |

---

## 2. Backup Schedules & Retention Matrix

```
[Nightly 02:00 UTC] ---> [pg_dump | gzip] ---> [Compute SHA-256] ---> [/app/backups/]
                                                                             |
                                                                             v
                                                                   [Sync to Encrypted S3]
```

| Backup Frequency | Storage Location | Retention Period | Encryption & Security |
| :--- | :--- | :--- | :--- |
| **Nightly Full Backup** | Local Host Volume (`/app/backups`) | 14 Days | Local directory permissions `0700` (`appuser`) |
| **Daily Remote Backup** | AWS S3 Bucket (`eazydoc-backups`) | 30 Days | SSE-S3 / KMS Encryption, Versioning Enabled |
| **Weekly Snapshot** | AWS S3 Cold Storage | 12 Weeks | S3 Glacier Flexible Retrieval |
| **Monthly Archive** | AWS S3 Compliance Vault | 1 Year (7 Years for Financials) | S3 Object Lock (WORM - Write Once, Read Many) |

---

## 3. Automated Backup Generation Script

Located at `scripts/backup_db.sh`:

```bash
#!/usr/bin/env bash
set -eo pipefail

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_DIR="/app/backups"
BACKUP_FILE="${BACKUP_DIR}/eazydoc_prod_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

# 1. Generate full database dump
PGPASSWORD="${DATABASE_PASSWORD}" pg_dump \
  -h "${DATABASE_HOST:-db}" \
  -U "${DATABASE_USER:-eazydoc_prod_user}" \
  -d "${DATABASE_NAME:-eazydoc_prod_db}" \
  --format=plain --no-owner --no-privileges | gzip > "${BACKUP_FILE}"

# 2. Compute SHA-256 Checksum
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"

# 3. Test Gzip Integrity
gzip -t "${BACKUP_FILE}"

# 4. Sync to Offsite Encrypted Cloud Storage (if AWS configured)
if [ -n "${AWS_STORAGE_BUCKET_NAME}" ]; then
  aws s3 cp "${BACKUP_FILE}" "s3://${AWS_STORAGE_BUCKET_NAME}/database_backups/" --sse AES256
  aws s3 cp "${BACKUP_FILE}.sha256" "s3://${AWS_STORAGE_BUCKET_NAME}/database_backups/" --sse AES256
fi

# 5. Local Rotation (Purge dumps older than 14 days)
find "${BACKUP_DIR}" -name "eazydoc_prod_*.sql.gz" -mtime +14 -delete
find "${BACKUP_DIR}" -name "eazydoc_prod_*.sql.gz.sha256" -mtime +14 -delete
```

---

## 4. Backup Monitoring & Failure Alerting

1. **Dashboard Monitoring**:
   - The Super Admin operations endpoint (`GET /api/v1/admin/dashboard/operations/`) verifies the freshness of the latest backup file:
     - `healthy`: Age $< 26$ hours.
     - `warning`: Age between $26$ and $48$ hours.
     - `critical`: Age $> 48$ hours or no backup found.
2. **Automated Alerting**:
   - If backup generation fails or exits with non-zero code, Celery task triggers a P1 alert to `#ops-alerts` on Slack / PagerDuty.

---

## 5. Step-by-Step Restoration Drill Procedure

> [!CAUTION]
> **RULE:** NEVER restore a test backup over the active production database. Always use an isolated drill container.

### Step 1: Spin Up Isolated Drill Database
```bash
docker run --name eazydoc_drill_db \
  -e POSTGRES_DB=eazydoc_drill \
  -e POSTGRES_USER=eazydoc_drill_user \
  -e POSTGRES_PASSWORD=drill_secret_pw \
  -d postgres:16-alpine
```

### Step 2: Verify Checksum and Decompress Backup
```bash
LATEST_BACKUP=$(ls -t /app/backups/eazydoc_prod_*.sql.gz | head -1)

# Check SHA256 integrity
sha256sum -c "${LATEST_BACKUP}.sha256"

# Stream into drill database
gunzip -c "${LATEST_BACKUP}" | docker exec -i eazydoc_drill_db psql -U eazydoc_drill_user -d eazydoc_drill
```

### Step 3: Run Database Sanity Verification
```sql
SELECT 
    (SELECT count(*) FROM accounts_user) AS total_users,
    (SELECT count(*) FROM clinics_clinic) AS total_clinics,
    (SELECT count(*) FROM doctors_doctor) AS total_doctors,
    (SELECT count(*) FROM appointments_appointment) AS total_appointments,
    (SELECT count(*) FROM payments_payment) AS total_payments,
    (SELECT count(*) FROM payments_commission_record) AS total_commissions;
```

### Step 4: Clean Up Drill Container
```bash
docker stop eazydoc_drill_db && docker rm eazydoc_drill_db
```

---

## 6. Disaster Recovery Roles & Responsibility

| Role | Designee / Title | Emergency Responsibilities |
| :--- | :--- | :--- |
| **Incident Commander** | Lead DevOps Engineer / SRE | Authorizes DR execution, coordinates failover |
| **Database Administrator**| Senior Backend Architect | Executes restore scripts, validates row-count checksums |
| **Communications Lead** | Product Launch Manager | Posts internal status updates, alerts clinic partners |
