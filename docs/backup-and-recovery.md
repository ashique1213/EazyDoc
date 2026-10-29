# EazyDoc — Database Backup & Disaster Recovery Strategy

## 1. Executive Summary & Recovery Objectives

EazyDoc is a multi-tenant healthcare appointment booking platform. Data durability and transactional integrity are mission-critical. The backup and disaster recovery architecture adheres to HIPAA, ISO 27001, and India's DPDP Act 2023 requirements.

### Recovery Objectives (RPO & RTO)

| Metric | Target | Operational Definition |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **$\le$ 15 minutes** | Maximum allowable data loss window in the event of catastrophic primary failure. Maintained via daily full database dumps plus continuous Write-Ahead Log (WAL) archiving. |
| **Recovery Time Objective (RTO)** | **$\le$ 30 minutes** | Maximum allowable downtime required to restore primary operational capability on staging or replacement infrastructure. |

---

## 2. Backup Topology & Architecture

### 2.1. Backup Schedule & Frequency

1. **Daily Full Logical Backups:**
   - Generated daily at 02:00 UTC (off-peak hours for Indian Standard Time).
   - Generated using PostgreSQL `pg_dump` in custom binary format (`-F c -Z 9`) with maximum level-9 zlib compression.
   - Verified immediately after creation via SHA-256 cryptographic checksum calculation.
2. **Point-In-Time Recovery (PITR) WAL Archiving:**
   - In production AWS RDS / self-hosted PostgreSQL, WAL segments are shipped continuously to a dedicated private S3 archive bucket every 5 minutes or on 16MB file fill.
   - Allows restoring transactions to any arbitrary second within the retention window.
3. **Pre-Deployment / Pre-Migration Snapshots:**
   - Automated full database backup triggered prior to running database migrations (`python manage.py migrate`).

### 2.2. Retention Policy

| Tier | Frequency | Retention Window | Storage Tier |
| :--- | :--- | :--- | :--- |
| **Operational Tier** | Daily Full | 30 Days | S3 Standard / Local NVMe |
| **Compliance Tier** | Weekly Full | 12 Weeks (90 Days) | S3 Standard-Infrequent Access (S3-IA) |
| **Archive Tier** | Monthly Full | 1 Year (365 Days) | S3 Glacier Flexible Retrieval with Object Lock |

Local backups on production application hosts are automatically pruned after 30 days by `scripts/backup_db.sh`.

---

## 3. Storage Isolation & Security Hardening

1. **Storage Separation:**
   - Backups are never stored solely on the primary database instance disk.
   - Backups are synced to an isolated, dedicated AWS S3 bucket in a separate AWS region (`ap-south-1` primary to `ap-southeast-1` disaster recovery secondary).
2. **Access Control & Permissions:**
   - Public access is permanently disabled via AWS S3 `BlockPublicAccess`.
   - Access is restricted exclusively via IAM Least Privilege roles assigned to the backup agent worker.
   - Direct SSH or FTP access to backup archives is prohibited.
3. **At-Rest Encryption:**
   - All backup files are encrypted with AES-256 using AWS Key Management Service (KMS) Customer Managed Keys (CMK) with automated annual key rotation.
   - Client-side or OpenSSL/GPG encryption is applied prior to offsite transport:
     ```bash
     openssl enc -aes-256-cbc -salt -pbkdf2 -in eazydoc.dump -out eazydoc.dump.enc -pass env:BACKUP_ENCRYPTION_KEY
     ```
4. **Immutability (WORM):**
   - Compliance archives utilize S3 Object Lock in Compliance Mode to prevent deletion or overwriting even by root account credentials.

---

## 4. Disaster Recovery & Restoration Procedures

### 4.1. Pre-Restoration Verification Checklist

- [ ] Confirm target environment is isolated (Staging, Dev, or newly provisioned Production).
- [ ] Verify that production traffic is routed away or maintenance mode is active.
- [ ] Confirm SHA-256 checksum of the backup archive matches the source checksum.
- [ ] Ensure database user has sufficient privileges (`CREATEDB`, `SUPERUSER` or owner privileges).

### 4.2. Step-by-Step Restoration Procedure

#### Step 1: Verify Backup Archive Cryptographic Checksum
```bash
sha256sum -c eazydoc_db_20261029_020000.dump.sha256
# Expected output: eazydoc_db_20261029_020000.dump: OK
```

#### Step 2: Decrypt Backup (if encrypted offsite)
```bash
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in eazydoc_db_20261029_020000.dump.enc \
  -out eazydoc_db_20261029_020000.dump \
  -pass env:BACKUP_ENCRYPTION_KEY
```

#### Step 3: Terminate Active Connections & Recreate Target Database
```sql
-- Terminate existing connections to target database
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'eazydoc_recovery_db' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS eazydoc_recovery_db;
CREATE DATABASE eazydoc_recovery_db WITH OWNER eazydoc_user ENCODING 'UTF8';
```

#### Step 4: Execute Restoration via pg_restore
```bash
pg_restore \
  -h localhost \
  -p 5432 \
  -U eazydoc_user \
  -d eazydoc_recovery_db \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  -v \
  eazydoc_db_20261029_020000.dump
```

#### Step 5: Post-Restoration Data Integrity Verification
Execute database record audit across critical tenant domains:
```bash
psql -h localhost -p 5432 -U eazydoc_user -d eazydoc_recovery_db -c "
SELECT 'users' AS table_name, count(*) AS records FROM accounts_user
UNION ALL
SELECT 'clinics', count(*) FROM clinics_clinic
UNION ALL
SELECT 'doctors', count(*) FROM doctors_doctor
UNION ALL
SELECT 'doctor_clinics', count(*) FROM doctor_clinics_doctorclinic
UNION ALL
SELECT 'schedules', count(*) FROM schedules_schedule
UNION ALL
SELECT 'appointments', count(*) FROM appointments_appointment
UNION ALL
SELECT 'payments', count(*) FROM payments_payment
UNION ALL
SELECT 'commission_records', count(*) FROM payments_commissionrecord
UNION ALL
SELECT 'notifications', count(*) FROM notifications_notification;
"
```

#### Step 6: Validate Django Migrations & Startup Check
```bash
python manage.py showmigrations --settings=config.settings.production
python manage.py check --deploy --settings=config.settings.production
```

---

## 5. Automated Verification & Testing Cadence

1. **Weekly Automated Restore Drills:**
   - An automated staging pipeline downloads the latest Sunday backup dump, restores it into a temporary ephemeral container, executes database integrity tests, and terminates the container.
2. **Audit Rule:**
   - *A backup is not verified until restoration has succeeded.* Backups without verified restore logs are marked UNVERIFIED in the compliance log.

