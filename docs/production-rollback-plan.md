# EazyDoc — Production Rollback Plan & Emergency Procedures

This document provides standardized, step-by-step procedures for safely rolling back releases, managing migration incompatibilities, and mitigating emergencies in the EazyDoc production environment.

---

## 1. Emergency Authorization Hierarchy

Only the following designated individuals are authorized to initiate a production rollback or emergency mitigation:

1. **Lead DevOps Engineer / SRE Commander** (Infrastructure & Container rollbacks)
2. **Senior Backend Architect** (Database migration rollbacks & forward fixes)
3. **Product Launch Manager** (Business-level emergency stop & maintenance mode)

---

## 2. Fast Rollback: Application Containers & Images

EazyDoc retains tagged Docker images for the previous stable release on the production host and container registry:

```bash
# Example image tags:
# eazydoc-backend:prod-v1.0.0 (Current)
# eazydoc-backend:prod-v0.9.8 (Previous Stable)
```

### 2.1 Backend / API Fast Rollback (< 5 Minutes)
If a newly deployed backend container exhibits unhandled exceptions, high latency, or boot failures:

```bash
# 1. Revert to previous release tag in Git
git checkout <previous_stable_tag_or_commit>

# 2. Rebuild or point compose to previous verified container image
docker compose -f docker-compose.prod.yml build backend celery celery-beat

# 3. Gracefully restart backend services
docker compose -f docker-compose.prod.yml up -d --no-deps backend celery celery-beat

# 4. Verify liveness probe
curl -f https://eazydoc.com/api/v1/health/live/
```

### 2.2 Frontend SPA Fast Rollback (< 3 Minutes)
If the frontend release suffers critical UI rendering errors or routing breaks:

```bash
# 1. Revert frontend commit
git checkout <previous_stable_tag> -- frontend/

# 2. Rebuild frontend production container
docker compose -f docker-compose.prod.yml build frontend

# 3. Restart frontend and reload Nginx
docker compose -f docker-compose.prod.yml up -d --no-deps frontend
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## 3. Database Migration Incidents & Forward-Fix Strategy

> [!CRITICAL]
> **Database Rollback Golden Rule**:
> NEVER attempt a destructive database rollback (`migrate <app> <previous_migration>`) if the migration removed columns or altered active patient/financial tables.
> **Prefer Forward-Fixes Over Destructive Rollbacks.**

### Scenario A: Additive Migration Failed During Deployment
If a new table or nullable column failed to create:
1. The migration transaction auto-aborts in PostgreSQL.
2. Revert the application container code to the previous release.
3. Database remains backward-compatible.

### Scenario B: Migration Caused Runtime Locking or Performance Degradation
1. Identify the blocking query PID in PostgreSQL:
   ```sql
   SELECT pid, query, state, now() - query_start AS duration 
   FROM pg_stat_activity 
   WHERE state != 'idle' ORDER BY duration DESC;
   ```
2. Terminate the blocking DDL:
   ```sql
   SELECT pg_cancel_backend(<pid>);
   ```
3. Prepare a forward-fix migration that applies indexes concurrently (`CREATE INDEX CONCURRENTLY`) without locking the table.

### Scenario C: Catastrophic Data Corruption (Zero-Loss Restore)
1. Place application in Maintenance Mode immediately via Nginx:
   ```bash
   # Return 503 Maintenance page to all public ingress
   docker compose -f docker-compose.prod.yml exec nginx sh -c "echo 'Service under maintenance' > /usr/share/nginx/html/maintenance.html"
   ```
2. Restore the pre-migration snapshot into an isolated verification database.
3. Extract any legitimate bookings created between the snapshot and the outage.
4. Restore database and replay missing transactions.
5. Resume traffic.

---

## 4. Payment Gateway Emergency Stop

If Razorpay gateway encounters duplicate charges, signature validation discrepancies, or upstream outages:

1. **Activate Circuit Breaker (API Level)**:
   Set `PAYMENT_GATEWAY_PAUSED=True` in `.env.production` and reload backend:
   ```bash
   docker compose -f docker-compose.prod.yml up -d backend
   ```
2. **Behavior**:
   - Booking initiation transitions to a temporary "Cash / Pay at Clinic" mode or holds appointments in `PENDING_CONFIRMATION` without triggering failed online payment loops.
   - Razorpay webhook listener continues to ingest and safely store incoming callbacks in `PaymentWebhookEvent` for retrospective reconciliation.

---

## 5. Security Incident & Data Breach Containment

If unauthorized cross-tenant data access or credential brute-forcing is detected:

1. **Isolate Compromised Accounts**:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c "
   from apps.accounts.models import User
   u = User.objects.get(email='compromised_account@example.com')
   u.is_active = False
   u.save()
   "
   ```
2. **Invalidate Active JWT Tokens**:
   Execute blacklist flush for affected users:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py flushexpiredtokens
   ```
3. **Firewall Block Attacking IPs**:
   Add attacker IP to Nginx `deny <ip>;` directive and reload Nginx.

---

## 6. Audit Trail Preservation

During any rollback or emergency mitigation:
- **NEVER truncate or purge `apps_audit_logs`, `payments_payment`, `payments_commission_record`, or `appointments_appointment_history`.**
- Financial and clinical audit logs must remain completely intact for regulatory and forensic post-mortems.
