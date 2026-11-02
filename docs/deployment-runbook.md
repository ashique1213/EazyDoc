# EazyDoc Deployment Runbook

This runbook serves as the primary operational guide for DevOps engineers, Site Reliability Engineers (SRE), and system administrators managing the EazyDoc staging and production environments.

---

## 1. System Architecture & Topology

```
                         [ Port 80 / 443 ]
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │     Nginx Gateway     │
                     └───────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [ Frontend (SPA) ]               [ Daphne ASGI:8000 ]
         (Static Nginx)                    (Backend API)
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                       [ PostgreSQL 16 (DB) ]           [ Redis 7 (Broker/Cache) ]
                                                                 │
                                                 ┌───────────────┴───────────────┐
                                                 ▼                               ▼
                                       [ Celery Worker ]                 [ Celery Beat ]
                                       (Task Execution)                (DatabaseScheduler)
```

---

## 2. Standard Deployment Procedure

### 2.1 Release Checklist
1. All automated tests passing: `python manage.py test` (311 tests passing).
2. Frontend build passing: `npm run lint && npm run build` (0 errors, 0 warnings).
3. Migration check clean: `python manage.py makemigrations --check --dry-run`.
4. Staging configuration confirmed: `.env.staging` populated with test keys and secure secrets.
5. Pre-deployment backup generated: `./scripts/backup_db.sh` or `.\scripts\backup_db.ps1`.

### 2.2 Execution Commands
```bash
# 1. Update source code
git checkout develop
git pull origin develop

# 2. Take pre-deployment database backup
./scripts/backup_db.sh

# 3. Build and launch updated staging containers
docker compose -f docker-compose.staging.yml up -d --build

# 4. Verify deployment health
python scripts/staging_health_check.py http://localhost
```

---

## 3. Celery Worker & Beat Operations

### 3.1 Process Management
- **Celery Worker:** Processes asynchronous email notifications, appointment reminder scheduling, and PDF document generation.
- **Celery Beat:** Dispatches periodic jobs using `django_celery_beat.schedulers:DatabaseScheduler`.

> [!CRITICAL]
> **Single Beat Scheduler Rule:** Never run more than one Celery Beat scheduler simultaneously for a single database. Multiple Beat instances will cause duplicate reminder and notification events.

### 3.2 Inspecting Worker Status
```bash
# Check worker status
docker compose -f docker-compose.staging.yml exec backend celery -A config inspect ping

# Check active tasks
docker compose -f docker-compose.staging.yml exec backend celery -A config inspect active

# Check scheduled periodic tasks
docker compose -f docker-compose.staging.yml exec backend celery -A config inspect scheduled
```

### 3.3 Restarting Workers
```bash
# Gracefully restart worker container
docker compose -f docker-compose.staging.yml restart celery

# Restart Beat scheduler
docker compose -f docker-compose.staging.yml restart celery-beat
```

---

## 4. Logging & Monitoring Playbook

### 4.1 Viewing Logs
```bash
# Real-time backend API logs
docker compose -f docker-compose.staging.yml logs -f --tail=100 backend

# Celery worker logs
docker compose -f docker-compose.staging.yml logs -f --tail=100 celery

# Celery Beat periodic scheduler logs
docker compose -f docker-compose.staging.yml logs -f --tail=100 celery-beat

# Nginx access and error logs
docker compose -f docker-compose.staging.yml logs -f --tail=100 nginx
```

### 4.2 Privacy & Sensitive Data Scrubbing
Application logs use structured formats. The following sensitive parameters are scrubbed:
- Passwords (`password`, `password_confirm`)
- Authorization headers (`Bearer <token>`)
- Cookie payloads (`access_token`, `refresh_token`)
- Payment gateway secrets (`key_secret`, `webhook_secret`)
- Webhook payloads: raw sensitive customer tokens are omitted; only `event`, `order_id`, and `amount` are recorded in audit logs.

---

## 5. Troubleshooting Playbook

### Incident 1: Backend Reports 503 "Service Unavailable" on `/api/v1/health/`
- **Cause:** Database or Redis container is unreachable.
- **Action:**
  1. Run `docker compose -f docker-compose.staging.yml ps` to check container health.
  2. If `db` is restarting or unhealthy, check logs: `docker compose -f docker-compose.staging.yml logs db`.
  3. Verify disk space: `df -h`. If disk is full, purge old Docker build caches (`docker system prune -f`).
  4. If Redis is down: `docker compose -f docker-compose.staging.yml restart redis`.

### Incident 2: POST Requests Fail with 403 "CSRF verification failed"
- **Cause:** Request origin is not included in `CSRF_TRUSTED_ORIGINS`.
- **Action:**
  1. Inspect browser request origin header (e.g. `https://staging.eazydoc.internal`).
  2. Verify that `CSRF_TRUSTED_ORIGINS` in `.env.staging` includes the exact scheme and domain.
  3. Restart backend: `docker compose -f docker-compose.staging.yml restart backend`.

### Incident 3: Razorpay Webhook Returns 400 Bad Request
- **Cause:** Webhook secret mismatch or corrupted request body.
- **Action:**
  1. Verify `RAZORPAY_WEBHOOK_SECRET` in `.env.staging` matches the secret configured in Razorpay test dashboard.
  2. Check Nginx configuration to ensure raw body bytes are preserved without modification.
  3. Inspect `payments_paymentwebhookevent` table:
     ```bash
     docker compose -f docker-compose.staging.yml exec backend python manage.py shell -c "
     from apps.payments.models import PaymentWebhookEvent
     print(PaymentWebhookEvent.objects.order_by('-created_at')[:5].values('event_id', 'status', 'error_message'))
     "
     ```

### Incident 4: Database Exclusion Constraint Error (`btree_gist`)
- **Cause:** Concurrent booking conflict or missing `btree_gist` extension in PostgreSQL.
- **Action:**
  1. Verify extension is installed:
     ```bash
     docker compose -f docker-compose.staging.yml exec db psql -U eazydoc_staging_user -d eazydoc_staging_db -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
     ```
  2. If an exclusion constraint rejected a slot booking, this is expected behavior under concurrency to prevent double bookings.

---

## 6. Disaster Recovery Runbook

In the event of database corruption or unrecoverable host failure:
1. Stop backend and workers to prevent new writes:
   ```bash
   docker compose -f docker-compose.staging.yml stop backend celery celery-beat
   ```
2. Locate the most recent valid backup in `backups/`.
3. Verify SHA-256 checksum:
   ```bash
   sha256sum -c backups/eazydoc_db_backup_<timestamp>.sql.gz.sha256
   ```
4. Execute restore:
   ```bash
   ./scripts/restore_db.sh backups/eazydoc_db_backup_<timestamp>.sql.gz
   ```
5. Restart services:
   ```bash
   docker compose -f docker-compose.staging.yml start backend celery celery-beat
   ```
6. Verify system health:
   ```bash
   python scripts/staging_health_check.py http://localhost
   ```

