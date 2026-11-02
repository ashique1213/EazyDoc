# Database Deployment, Migration, and Rollback Procedures

This document outlines the standard operational procedures for deploying, migrating, validating, and rolling back the PostgreSQL database in the EazyDoc staging and production environments.

---

## 1. Database Connection Configuration

EazyDoc uses PostgreSQL 16 Alpine as its primary relational store. In containerized staging, connection parameters are supplied via environment variables (`.env.staging`):

```env
DATABASE_NAME=eazydoc_staging_db
DATABASE_USER=eazydoc_staging_user
DATABASE_PASSWORD=<secure_password>
DATABASE_HOST=db
DATABASE_PORT=5432
CONN_MAX_AGE=60
```

Django resolves the connection via `dj-database-url` or individual settings in `backend/config/settings/base.py`:
```python
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"postgresql://{env('DATABASE_USER')}:{env('DATABASE_PASSWORD')}@{env('DATABASE_HOST')}:{env('DATABASE_PORT')}/{env('DATABASE_NAME')}",
    )
}
```

---

## 2. Pre-Deployment Database Backup

> [!IMPORTANT]
> **Strict Operational Rule:** Always take an atomic, compressed snapshot of the database immediately before applying any schema migrations or releasing new code. Never drop or reset existing databases to resolve migration issues.

### 2.1 Generating a Pre-Migration Backup

**Using Linux / macOS Bash:**
```bash
./scripts/backup_db.sh
```

**Using Windows PowerShell:**
```powershell
.\scripts\backup_db.ps1
```

The backup scripts execute `pg_dump -Fc` (custom binary format), gzip compress the archive, and generate a cryptographic SHA-256 integrity checksum:
```text
Backups created in: /opt/eazydoc/backups/ (or .\backups\)
  File: eazydoc_db_backup_20261102_140000.sql.gz
  Checksum: eazydoc_db_backup_20261102_140000.sql.gz.sha256
```

---

## 3. Migration Consistency & Safety Checks

Before applying migrations to staging, verify that all local model changes are captured and that migrations are strictly linear:

### 3.1 Migration Dry-Run Check
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py makemigrations --check --dry-run
```
**Expected Outcome:** `No changes detected`. If changes are detected, uncommitted model modifications must be generated and tested in development before proceeding.

### 3.2 Inspect Migration Plan
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py showmigrations
```
Verify that all dependencies form a clean, non-conflicting directed acyclic graph.

---

## 4. Applying Migrations Safely

### 4.1 Automatic Execution (Container Startup)
In `docker-compose.staging.yml`, `backend/entrypoint.sh` executes migrations automatically when `RUN_MIGRATIONS=true`:
```bash
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput
fi
```

### 4.2 Manual Execution (Interactive / Staging Deployments)
If executing migrations manually:
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py migrate --noinput
```

---

## 5. Post-Migration Verification

After applying migrations, verify that the schema, extensions, and critical constraints exist:

### 5.1 Database Connectivity & Health
```bash
docker compose -f docker-compose.staging.yml exec backend python -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT 1;')
    row = cursor.fetchone()
    print('PostgreSQL Connection: OK (Result:', row[0], ')')
"
```

### 5.2 Verify PostgreSQL Extensions (`btree_gist`)
EazyDoc uses PostgreSQL exclusion constraints (`apps/appointments/migrations/0002_postgres_exclusion_constraint.py`) to prevent concurrent double-booking of overlapping intervals:
```bash
docker compose -f docker-compose.staging.yml exec db psql -U eazydoc_staging_user -d eazydoc_staging_db -c "
SELECT extname, extversion FROM pg_extension WHERE extname = 'btree_gist';
"
```
**Expected Output:** `btree_gist` extension must be installed and active.

### 5.3 Verify Critical Tables & Indexes
```bash
docker compose -f docker-compose.staging.yml exec db psql -U eazydoc_staging_user -d eazydoc_staging_db -c "
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'appointments_%';
"
```

---

## 6. Migration Failure and Rollback Procedures

If a migration fails during deployment (e.g. timeout, lock contention, or syntax incompatibility):

### Step 6.1: Identify the Failing Migration
Inspect the error output from `python manage.py migrate`. Note the app name and the migration number (e.g. `appointments:0005_failing_migration`).

### Step 6.2: Revert to the Previous Migration
Django supports rolling back migrations to a previous state:
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py migrate <app_name> <previous_migration_name>
# Example:
# docker compose -f docker-compose.staging.yml exec backend python manage.py migrate appointments 0004_appointment_payment_status_and_more
```

### Step 6.3: Full Database Disaster Recovery Rollback
If schema corruption occurs or tables are left in an indeterminate state, execute a full restore from the pre-deployment backup:

**Using Linux / macOS Bash:**
```bash
./scripts/restore_db.sh backups/eazydoc_db_backup_20261102_140000.sql.gz
```

**Using Windows PowerShell:**
```powershell
.\scripts\restore_db.ps1 -BackupFile .\backups\eazydoc_db_backup_20261102_140000.sql.gz
```

The restore script:
1. Validates the SHA-256 checksum to prevent corrupt data restoration.
2. Terminates active client connections to PostgreSQL.
3. Recreates the clean database schema.
4. Restores all tables, constraints, sequences, and indexes using `pg_restore`.
5. Validates connection health post-restoration.

