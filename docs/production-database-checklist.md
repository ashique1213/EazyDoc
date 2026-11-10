# EazyDoc — Production Database Preparation & Migration Checklist

This document details the database readiness checks, constraint validation, migration verification, and safe execution protocol for the EazyDoc production PostgreSQL database.

---

## 1. Database Schema & Constraint Inventory

| Table | Constraint / Index Type | Target Entity / Field | Purpose & Behavior |
| :--- | :--- | :--- | :--- |
| `accounts_user` | Unique Constraint | `email` | Unique user identity across all tenant roles |
| `clinics_clinic` | Foreign Key (`PROTECT`)| `owner_id` | Prevents deleting a user who owns an active clinic |
| `doctors_doctor` | Unique Index | `normalized_registration_number`, `normalized_registration_council` | Eliminates duplicate doctor medical registrations |
| `clinics_doctorclinic`| Unique Constraint | `doctor_id`, `clinic_id` | Enforces single active affiliation per doctor-clinic pair |
| `appointments_appointment`| Unique Index | `booking_reference` | Fast O(1) lookup; prevents duplicate booking codes |
| `appointments_appointment`| Foreign Key (`PROTECT`)| `patient_id`, `doctor_id`, `clinic_id` | Preserves audit trail; rejects cascading deletes |
| `payments_payment` | Check Constraint | `amount >= 0.00` | Eliminates negative payment records |
| `payments_commission_record`| OneToOne (`PROTECT`)| `payment_id` | Exactly one immutable commission record per payment |
| `payments_commission_record`| Decimal Check | `gross_amount = commission_amount + clinic_share` | Enforces double-entry financial accounting invariant |
| `payments_webhook_event`| Unique Index | `event_id` | Enforces webhook idempotency and replay protection |

---

## 2. Migration Consistency Verification

### 2.1 Unapplied Migration Check
Execute in the backend directory:
```bash
python manage.py makemigrations --check --dry-run
```
- **Observed Result:** `No changes detected` (Models match migrations 100%).

### 2.2 Migration Status Check
```bash
python manage.py showmigrations
```
- **Requirement:** All migrations across all apps (`accounts`, `clinics`, `doctors`, `schedules`, `appointments`, `payments`, `notifications`, `reviews`, `analytics`, `audit_logs`) must show `[X]`.

---

## 3. Pre-Migration Protocol (Controlled Deployment Window)

Every production schema migration must follow this exact 6-step lifecycle:

```
[Step 1: Backup] ---> [Step 2: Verify Checksum] ---> [Step 3: Review SQL]
                                                               |
[Step 6: Verify Probes] <--- [Step 5: Apply Migration] <--- [Step 4: Check Non-Destructive]
```

### Step 1: Take Pre-Migration Database Backup
```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U eazydoc_prod_user -d eazydoc_prod_db --format=plain --no-owner | gzip > /app/backups/pre_migration_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Step 2: Verify Backup Integrity
```bash
gzip -t /app/backups/pre_migration_backup_*.sql.gz && echo "Backup verified clean."
```

### Step 3: Review Migration SQL Output
Prior to applying any new migration, inspect the raw DDL statements:
```bash
python manage.py sqlmigrate <app_name> <migration_number>
```
Verify that:
- Indexes are created concurrently if table size exceeds 100,000 rows.
- No `DROP TABLE`, `DROP COLUMN`, or `TRUNCATE` operations are present.

### Step 4: Verify Migration is Non-Destructive
- Destructive schema changes (column removals, table renames) are strictly prohibited in a single release.
- Use the **Expand/Contract Pattern**: Add new nullable columns first (Expand), migrate data in background, and deprecate old columns in a subsequent release (Contract).

### Step 5: Execute Migration in Controlled Window
```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Step 6: Post-Migration Health Verification
```bash
curl -f https://eazydoc.com/api/v1/health/ready/
# Must return {"status": "ok", "database": "ok", "redis": "ok"} with HTTP 200
```

---

## 4. Production Database Guardrails

> [!CRITICAL]
> **Strict Operational Prohibitions**:
> - NEVER run `python manage.py flush` in production or staging.
> - NEVER drop or recreate the production database to fix an application defect.
> - NEVER modify patient medical records, consultation notes, or audit history directly via raw SQL `UPDATE` or `DELETE`.
> - Always execute administrative corrections via Django migrations or validated management commands wrapped in `transaction.atomic()`.

