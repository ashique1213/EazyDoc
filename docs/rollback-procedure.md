# EazyDoc Deployment Rollback Procedure

This document defines the emergency rollback protocols for the EazyDoc platform when a release in staging or production encounters unrecoverable errors, severe performance degradation, or data-integrity risks.

---

## 1. Rollback Criteria & Authority

A rollback must be initiated immediately if any of the following conditions occur post-deployment:
1. **Critical Service Failure:** Core API returns HTTP 5xx errors affecting > 5% of requests.
2. **Database Migration Failure:** A schema migration causes deadlocks, crashes, or data corruption.
3. **Data Isolation Breach:** Cross-tenant leakage or authorization bypass is detected.
4. **Payment Gateway Disruption:** Webhooks or checkout verifications consistently fail.
5. **Background Queue Stoppage:** Celery worker or Beat scheduler crashes repeatedly.

**Recovery Time Objective (RTO):** $\le$ 30 minutes.

---

## 2. Rollback Tiers Overview

Depending on the nature of the issue, choose the appropriate rollback tier:

| Tier | Failure Scope | Rollback Action | Estimated Time |
|---|---|---|---|
| **Tier 1: Container / Image Reversion** | Code regression or frontend bug (no schema changes) | Revert Docker images to previous tag | 3 - 5 minutes |
| **Tier 2: Django Migration Reversion** | Faulty migration (data intact, schema reversible) | Run `python manage.py migrate <app> <target>` | 5 - 10 minutes |
| **Tier 3: Full Disaster Recovery** | Database corruption or schema failure | Restore database snapshot from pre-deployment backup | 15 - 25 minutes |

---

## 3. Tier 1: Container & Application Reversion (No DB Changes)

When the database schema remains valid and only application code or frontend assets must be rolled back:

### Step 3.1: Stop Web Traffic
Prevent user requests from encountering errors during the transition:
```bash
docker compose -f docker-compose.staging.yml stop nginx backend frontend
```

### Step 3.2: Revert Code to Previous Git Release / Tag
```bash
git checkout <previous_stable_commit_or_tag>
# Example: git checkout 722bf6e
```

### Step 3.3: Rebuild and Start Containers
```bash
docker compose -f docker-compose.staging.yml up -d --build backend frontend nginx celery celery-beat
```

### Step 3.4: Verify Health
```bash
python scripts/staging_health_check.py http://localhost
```

---

## 4. Tier 2: Migration Reversion (Reversible Schema Changes)

If a newly applied migration introduced a query error or index lock, but the database schema can be cleanly reversed:

### Step 4.1: Stop Celery Workers & Beat
Stop asynchronous processing to prevent tasks from writing during migration rollback:
```bash
docker compose -f docker-compose.staging.yml stop celery celery-beat
```

### Step 4.2: Reverse the Specific App Migration
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py migrate <app_name> <previous_migration_name>
```

*Example:* To roll back `appointments` migration `0004` back to `0003`:
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py migrate appointments 0003_appointmenthistory_appointment_cancellation_reason_and_more
```

### Step 4.3: Restart Workers & Verify
```bash
docker compose -f docker-compose.staging.yml start celery celery-beat
docker compose -f docker-compose.staging.yml restart backend
python scripts/staging_health_check.py http://localhost
```

---

## 5. Tier 3: Full Database Disaster Recovery Rollback

When a migration causes schema corruption, irreversible data alteration, or cannot be rolled back via Django:

### Step 5.1: Stop All Writing Containers
Immediately stop web and background workers to prevent database modifications:
```bash
docker compose -f docker-compose.staging.yml stop backend celery celery-beat
```

### Step 5.2: Locate Pre-Deployment Database Snapshot
Identify the backup archive generated immediately prior to the deployment (located in `backups/`):
```text
backups/eazydoc_db_backup_<YYYYMMDD_HHMMSS>.sql.gz
```

### Step 5.3: Verify Checksum Integrity
Verify the SHA-256 integrity checksum:
```bash
# On Linux / macOS:
sha256sum -c backups/eazydoc_db_backup_<timestamp>.sql.gz.sha256

# On Windows PowerShell:
$expected = (Get-Content .\backups\eazydoc_db_backup_<timestamp>.sql.gz.sha256).Trim()
$actual = (Get-FileHash .\backups\eazydoc_db_backup_<timestamp>.sql.gz -Algorithm SHA256).Hash.ToLower()
if ($expected -ne $actual) { Write-Error "Checksum mismatch!" }
```

### Step 5.4: Execute Automated Restoration

**Using Linux / macOS Bash:**
```bash
./scripts/restore_db.sh backups/eazydoc_db_backup_<timestamp>.sql.gz
```

**Using Windows PowerShell:**
```powershell
.\scripts\restore_db.ps1 -BackupFile .\backups\eazydoc_db_backup_<timestamp>.sql.gz
```

### Step 5.5: Checkout Previous Code Base & Restart
```bash
git checkout <previous_stable_commit>
docker compose -f docker-compose.staging.yml up -d --build
```

### Step 5.6: Post-Rollback Validation
1. Verify system health:
   ```bash
   python scripts/staging_health_check.py http://localhost
   ```
2. Verify database connection:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py check
   ```
3. Run automated verification suite:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py test tests.test_staging_e2e_verification
   ```

---

## 6. Post-Mortem and Incident Reporting

Following any rollback:
1. Preserve error logs from all containers before rebuilding or pruning:
   ```bash
   docker compose -f docker-compose.staging.yml logs > incident_logs_$(date +%Y%m%d).log
   ```
2. Document the root cause in an incident report.
3. Create reproducing automated tests before attempting future deployment.

