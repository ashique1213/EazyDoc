# EazyDoc — Incident Response Runbooks & Disaster Recovery

This document provides standardized, step-by-step incident response procedures for on-call engineers, SREs, and DevOps personnel managing the EazyDoc multi-tenant healthcare platform.

---

## Incident Severity Classification

| Level | Definition | Response SLA | Notification Channels |
| :--- | :--- | :--- | :--- |
| **P1 — Critical** | Complete service outage, database down, payment system failure, cross-tenant data leak | 15 minutes | PagerDuty, SMS, Call, `#incident-p1` |
| **P2 — Major** | Partial service outage, high latency (>2s), Celery worker crash, webhook failure spike | 30 minutes | PagerDuty, Slack `#incident-p2` |
| **P3 — Moderate** | Degraded non-critical feature (e.g. notifications delayed, non-blocking report export failure) | 2 hours | Slack `#alerts-ops` |
| **P4 — Minor** | Minor cosmetic defect, non-impactful log noise, low-priority disk usage | 1 business day | Jira backlog, `#alerts-ops` |

---

## Runbook 1: API Complete Outage (502 Bad Gateway / 503 Service Unavailable / Unresponsive)

### Detection
- Nginx access log returning continuous HTTP 502/503.
- Liveness probe (`/api/v1/health/live/`) or readiness probe (`/api/v1/health/ready/`) timing out or returning 503.
- Automated uptime monitor (UptimeRobot / Sentry) triggering P1 alert.

### Immediate Actions (First 5 Minutes)
1. Verify host reachability via SSH.
2. Check container status:
   ```bash
   docker compose -f docker-compose.staging.yml ps
   ```
3. Check Nginx and Daphne error logs:
   ```bash
   docker compose -f docker-compose.staging.yml logs --tail=100 backend
   docker compose -f docker-compose.staging.yml logs --tail=100 nginx
   ```

### Diagnostic Steps
1. Probe Daphne ASGI directly inside the Docker network:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend curl -i http://localhost:8000/api/v1/health/live/
   ```
2. Check CPU and memory utilization on the host:
   ```bash
   docker stats --no-stream
   ```
3. Check if Daphne exited due to unhandled startup crash or OOM kill:
   ```bash
   docker inspect eazydoc_backend_staging --format='{{.State.Status}} (ExitCode: {{.State.ExitCode}})'
   ```

### Resolution
- **Case A: Backend container crashed/restarting**:
  Restart the backend service:
  ```bash
  docker compose -f docker-compose.staging.yml restart backend
  ```
- **Case B: Daphne hung due to deadlocked database transactions**:
  Inspect database locks (see Runbook 2), then restart backend:
  ```bash
  docker compose -f docker-compose.staging.yml restart backend
  ```
- **Case C: Nginx upstream socket misconfiguration**:
  Reload Nginx configuration:
  ```bash
  docker compose -f docker-compose.staging.yml exec nginx nginx -s reload
  ```

### Verification
```bash
curl -f https://staging.eazydoc.com/api/v1/health/live/
# Expected: {"status": "ok", "service": "eazydoc-api"} with HTTP 200
```

### Post-Incident Actions
- Review Daphne application logs prior to the crash for uncaught exceptions.
- Ensure Docker restart policy is `unless-stopped`.

---

## Runbook 2: Database Connection Exhaustion

### Detection
- Django error log: `django.db.utils.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections`.
- Readiness probe returns 503 with `"database": "unavailable"`.
- Active connections alert > 85% of `max_connections`.

### Immediate Actions (First 5 Minutes)
1. Log into the database container using superuser credentials:
   ```bash
   docker compose -f docker-compose.staging.yml exec db psql -U postgres -d eazydoc_staging_db
   ```
2. Terminate idle-in-transaction connections immediately:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle in transaction' 
     AND now() - state_change > interval '30 seconds';
   ```

### Diagnostic Steps
1. Count connection states:
   ```sql
   SELECT state, count(*) FROM pg_stat_activity GROUP BY state ORDER BY count DESC;
   ```
2. Identify application sources exhausting connections:
   ```sql
   SELECT usename, client_addr, count(*) FROM pg_stat_activity GROUP BY usename, client_addr;
   ```
3. Identify long-running queries holding locks:
   ```sql
   SELECT pid, now() - query_start AS duration, query 
   FROM pg_stat_activity 
   WHERE state != 'idle' 
   ORDER BY duration DESC LIMIT 10;
   ```

### Resolution
1. Terminate offending long-running blocking query:
   ```sql
   SELECT pg_terminate_backend(<pid>);
   ```
2. If Daphne workers are leaking connections, recycle backend containers:
   ```bash
   docker compose -f docker-compose.staging.yml restart backend
   ```
3. If traffic has permanently grown, increase `max_connections` in `postgresql.conf` and adjust `CONN_MAX_AGE` (see `docs/database-monitoring.md`).

### Verification
```sql
SELECT count(*) FROM pg_stat_activity;
-- Verify connection count drops below 40% of max_connections.
```

### Post-Incident Actions
- Verify `CONN_MAX_AGE = 60` is properly configured in Django.
- Review recent query deployments for missing `select_related` or unclosed transactions.

---

## Runbook 3: Redis Failure / Cache Outage

### Detection
- Sentry alerts: `redis.exceptions.ConnectionError: Error connecting to redis:6379`.
- Celery tasks stop being acknowledged.
- Rate limiter (`django-ratelimit`) fails closed or logs warnings.
- Readiness probe reports `"redis": "unavailable"`.

### Immediate Actions (First 5 Minutes)
1. Check Redis container status:
   ```bash
   docker compose -f docker-compose.staging.yml ps redis
   ```
2. Test Redis responsiveness:
   ```bash
   docker compose -f docker-compose.staging.yml exec redis redis-cli ping
   ```

### Diagnostic Steps
1. Review Redis container logs:
   ```bash
   docker compose -f docker-compose.staging.yml logs --tail=100 redis
   ```
2. Check if Redis ran out of memory:
   ```bash
   docker compose -f docker-compose.staging.yml exec redis redis-cli info memory
   ```
3. Check Redis persistence disk space (AOF / RDB):
   ```bash
   df -h /var/lib/docker/volumes/*redis*
   ```

### Resolution
- **If Redis container exited**:
  ```bash
  docker compose -f docker-compose.staging.yml restart redis
  ```
- **If Redis is Out of Memory (OOM)**:
  Flush volatile cache keys while preserving Celery queues (Queue is in DB 0, Cache in DB 1):
  ```bash
  docker compose -f docker-compose.staging.yml exec redis redis-cli -n 1 FLUSHDB
  ```
- **Restart Celery workers to re-establish broken socket pools**:
  ```bash
  docker compose -f docker-compose.staging.yml restart celery celery-beat
  ```

### Verification
```bash
docker compose -f docker-compose.staging.yml exec redis redis-cli ping
# Expected: PONG
```

### Post-Incident Actions
- Ensure `maxmemory` and `maxmemory-policy allkeys-lru` are configured for Redis cache instances.

---

## Runbook 4: Celery Worker Crash or Task Backlog Spike

### Detection
- Celery worker status in Super Admin operations endpoint shows `no_workers_detected` or `broker_unreachable`.
- `overdue_pending_reminders` increases above 25.
- Redis queue length (`LLEN celery`) grows rapidly.

### Immediate Actions (First 5 Minutes)
1. Inspect running Celery containers:
   ```bash
   docker compose -f docker-compose.staging.yml ps celery celery-beat
   ```
2. Check Celery worker logs for unhandled fatal errors:
   ```bash
   docker compose -f docker-compose.staging.yml logs --tail=100 celery
   ```

### Diagnostic Steps
1. Check active Celery tasks:
   ```bash
   docker compose -f docker-compose.staging.yml exec celery celery -A config inspect active
   ```
2. Check task queue backlog in Redis:
   ```bash
   docker compose -f docker-compose.staging.yml exec redis redis-cli LLEN celery
   ```
3. Check for stuck or hanging tasks exceeding soft/hard time limits.

### Resolution
1. Restart the Celery worker container:
   ```bash
   docker compose -f docker-compose.staging.yml restart celery
   ```
2. If backlog exceeds 1,000 tasks, scale worker concurrency temporarily:
   ```bash
   # Run with concurrency 4 temporarily to drain queue
   docker compose -f docker-compose.staging.yml up -d --scale celery=2
   ```
3. If tasks are repeatedly failing due to a third-party service outage (e.g. SMS provider), pause affected scheduled tasks until provider resolves.

### Verification
```bash
docker compose -f docker-compose.staging.yml exec celery celery -A config inspect ping
# Expected: celery@...: OK
```

### Post-Incident Actions
- Ensure all Celery tasks specify `time_limit=300` and `soft_time_limit=240`.
- Verify Celery `acks_late=True` prevents task drops on restarts.

---

## Runbook 5: Razorpay Payment Webhook Failure Spike

### Detection
- Alert: Webhook failure rate > 10% in last hour.
- `PaymentWebhookEvent.objects.filter(status='FAILED')` count spiking.
- Patient complaints of paid appointments remaining `PENDING_CONFIRMATION`.

### Immediate Actions (First 5 Minutes)
1. Inspect recent failed webhook records in Django admin or via shell:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py shell -c "
   from apps.payments.models import PaymentWebhookEvent, WebhookProcessingStatus
   failed = PaymentWebhookEvent.objects.filter(status=WebhookProcessingStatus.FAILED).order_by('-received_at')[:5]
   for f in failed:
       print(f.event_id, f.event_type, f.error_message)
   "
   ```

### Diagnostic Steps
1. Verify if failures are due to signature mismatch:
   - Check if `RAZORPAY_WEBHOOK_SECRET` was rotated or misconfigured.
2. Check Razorpay Status page (`status.razorpay.com`) for upstream gateway outages.
3. Verify if database deadlock occurred during appointment status updates.

### Resolution
1. If secret mismatch, update `RAZORPAY_WEBHOOK_SECRET` in `.env.staging` and reload backend:
   ```bash
   docker compose -f docker-compose.staging.yml up -d backend
   ```
2. Replay all failed webhooks safely via management command:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py replay_failed_webhooks
   ```

### Verification
- Check Super Admin Operations dashboard (`/api/v1/admin/dashboard/operations/`).
- Verify `webhooks.failed` count stops increasing and `webhooks.processed` increments.

### Post-Incident Actions
- Implement alert notification when webhook signature failures exceed 3 consecutive events.

---

## Runbook 6: Double-Booking Race Condition Detection

### Detection
- Error log: `IntegrityError` or `BookingConflictError`.
- Multiple appointments sharing overlapping `(doctor_clinic_id, slot_start, slot_end)` with status `CONFIRMED`.

### Immediate Actions (First 5 Minutes)
1. Execute overlap detection SQL query:
   ```sql
   SELECT a1.id, a1.booking_reference, a2.id, a2.booking_reference, a1.doctor_clinic_id, a1.start_time, a1.end_time
   FROM appointments_appointment a1
   JOIN appointments_appointment a2 ON a1.doctor_clinic_id = a2.doctor_clinic_id
     AND a1.id != a2.id
     AND a1.status = 'CONFIRMED' AND a2.status = 'CONFIRMED'
     AND tstzrange(a1.start_time, a1.end_time) && tstzrange(a2.start_time, a2.end_time);
   ```

### Diagnostic Steps
1. Check booking trace IDs in structured logs to determine the exact timestamp sequence.
2. Verify if `select_for_update()` was bypassed in any custom booking path or management script.

### Resolution
1. Identify the later booking of the conflict.
2. Transition the second booking to `RESCHEDULE_REQUIRED` and trigger patient notification:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py flag_double_booking --appointment-id=<id>
   ```
3. Issue full refund or prioritize slot rescheduling for affected patient.

### Verification
- Re-run the overlap detection query; verify zero rows returned.

### Post-Incident Actions
- Verify database exclusion constraint (`btree_gist`) or table row locks on `DoctorSchedule` / `DoctorClinic`.

---

## Runbook 7: Multi-Tenant Data Leak or Cross-Tenant Access Attempt

### Detection
- Sentry alert: `TenantAccessViolation` or `PermissionDenied` on clinic endpoints.
- Audit log showing actor from Clinic A requesting Clinic B resource ID.
- HTTP 403 Forbidden spikes on clinic management routes.

### Immediate Actions (First 5 Minutes)
1. Extract actor IP and user ID from the structured log using the correlation ID:
   ```bash
   docker compose -f docker-compose.staging.yml logs backend | grep "TenantAccessViolation"
   ```
2. Suspend the offending account immediately to prevent further exfiltration:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py shell -c "
   from apps.accounts.models import User
   u = User.objects.get(email='suspicious_user@example.com')
   u.is_active = False
   u.save()
   "
   ```

### Diagnostic Steps
1. Trace all actions performed by the suspicious user across the audit log:
   ```sql
   SELECT timestamp, action, resource, ip_address 
   FROM audit_logs_auditlog 
   WHERE actor_id = '<user_uuid>' 
   ORDER BY timestamp DESC;
   ```
2. Review the API endpoint code to verify if queryset tenant filtering (`filter(clinic=request.user.clinic)`) was omitted.

### Resolution
1. Hotfix the affected endpoint by ensuring `get_queryset()` enforces tenant boundary.
2. Rotate API keys or session tokens if credentials were compromised.
3. If data was exposed, initiate standard GDPR/HIPAA notification protocol.

### Verification
- Execute automated regression test `test_multi_tenant_isolation.py` against the fix.

### Post-Incident Actions
- Add automated security linting to flag un-scoped `Model.objects.all()` in clinic views.

---

## Runbook 8: High API Latency (> 2s Sustained)

### Detection
- P95 response time alert > 2,000 ms.
- Nginx upstream response time logs showing slow processing.
- Frontend users experiencing spinners and slow page loads.

### Immediate Actions (First 5 Minutes)
1. Check Super Admin operations dashboard for DB and Redis latency values.
2. Check database for slow running queries (Runbook 2).
3. Inspect Nginx request logs for the slowest endpoints:
   ```bash
   docker compose -f docker-compose.staging.yml logs nginx | grep -o 'request_time=[0-9.]*' | sort -nr | head -20
   ```

### Diagnostic Steps
1. Run `pg_stat_statements` to identify the query consuming the highest total time.
2. Verify Redis network latency from backend:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python -c "
   import redis, time, os
   r = redis.from_url(os.environ['REDIS_URL'])
   t0 = time.perf_counter()
   r.ping()
   print('Latency:', round((time.perf_counter() - t0)*1000, 2), 'ms')
   "
   ```

### Resolution
- Add missing database index identified via `EXPLAIN ANALYZE`.
- Clear bloated cache keys or scale Daphne worker concurrency.

### Verification
- Confirm P95 response times normalize below 300 ms.

---

## Runbook 9: High Error Rate (> 5% 5xx Errors)

### Detection
- HTTP 500 error count spikes in Sentry.
- Nginx log analysis shows > 5% status 500 / 502 / 504 over a 5-minute rolling window.

### Immediate Actions (First 5 Minutes)
1. Check Sentry dashboard for the top recurring exception fingerprint.
2. Search backend logs for unhandled exceptions with request IDs:
   ```bash
   docker compose -f docker-compose.staging.yml logs backend | grep "Unhandled server exception"
   ```

### Diagnostic Steps
1. Determine if error is localized to a specific endpoint (e.g. payments, reviews) or system-wide.
2. Inspect recent code changes deployed in the last release.

### Resolution
1. If caused by a newly deployed bad release, execute rollback immediately (see `docs/rollback-procedure.md`):
   ```bash
   git checkout <previous_stable_tag>
   docker compose -f docker-compose.staging.yml build backend
   docker compose -f docker-compose.staging.yml up -d backend
   ```
2. If caused by external API outage (e.g. Razorpay/SMS), enable graceful degradation flag.

### Verification
- Confirm 5xx rate drops below 0.1% of total requests.

---

## Runbook 10: Disk Space Exhaustion (> 90% Full)

### Detection
- Host disk utilization alert > 90%.
- PostgreSQL error: `PANIC: could not write to file ... No space left on device`.
- Docker daemon unable to start new containers.

### Immediate Actions (First 5 Minutes)
1. Check filesystem disk usage:
   ```bash
   df -h
   ```
2. Identify largest Docker volumes:
   ```bash
   docker system df -v
   ```

### Diagnostic Steps
1. Inspect directory breakdown:
   ```bash
   du -sh /var/lib/docker/volumes/* | sort -hr | head -10
   ```
2. Check for runaway log files or old uncompressed database dumps:
   ```bash
   find /var/log /tmp /app/backups -type f -size +100M
   ```

### Resolution
1. Prune dangling Docker containers, images, and build cache:
   ```bash
   docker system prune -af --volumes=false
   ```
2. Compress or rotate older database backup files:
   ```bash
   find /app/backups -name "*.sql" -mtime +7 -exec gzip {} \;
   find /app/backups -name "*.sql.gz" -mtime +30 -delete
   ```
3. Truncate oversized container logs:
   ```bash
   truncate -s 0 /var/lib/docker/containers/*/*-json.log
   ```

### Verification
```bash
df -h
# Verify available disk space is > 30%.
```

### Post-Incident Actions
- Implement automated log rotation with `max-size: 50m` and `max-file: 3` in `docker-compose.yml`.

---

## Runbook 11: Memory Leak or OOM Container Restarts

### Detection
- Docker container unexpectedly terminates with Exit Code 137 (SIGKILL by Linux OOM killer).
- Host RAM usage continuously climbing without leveling off.
- Sentry alert: `MemoryError`.

### Immediate Actions (First 5 Minutes)
1. Inspect dmesg for OOM kills:
   ```bash
   dmesg -T | grep -i oom
   ```
2. Check memory usage by container:
   ```bash
   docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
   ```

### Diagnostic Steps
1. Identify which container exceeded limits (Backend Daphne or Celery worker).
2. Check if Celery workers are retaining memory across long-running tasks.

### Resolution
1. Restart the memory-bloated container:
   ```bash
   docker compose -f docker-compose.staging.yml restart celery
   ```
2. Enforce `CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000` to auto-recycle worker processes.
3. Configure explicit container memory limits in `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1024M
   ```

### Verification
- Monitor memory usage stability over a 30-minute period under normal traffic.

---

## Runbook 12: Security Breach or Suspicious Authentication Spike

### Detection
- Rapid spike in failed login attempts (`apps.accounts.views` WARNINGs).
- Rate-limiting threshold (`LoginRateThrottle`) triggered repeatedly across multiple IPs.
- Suspicious credential stuffing or brute-force pattern targeting doctor/admin accounts.

### Immediate Actions (First 5 Minutes)
1. Extract attacking IP addresses from Nginx logs:
   ```bash
   docker compose -f docker-compose.staging.yml logs nginx \
     | grep "/api/v1/auth/login/" \
     | awk '{print $1}' | sort | uniq -c | sort -nr | head -20
   ```
2. Block attacking IP addresses immediately at firewall / Nginx level:
   ```bash
   # Add to Nginx blocklist or cloud security group
   iptables -A INPUT -s <attacker_ip> -j DROP
   ```

### Diagnostic Steps
1. Check if any attempts succeeded from the attacking IP addresses:
   ```bash
   docker compose -f docker-compose.staging.yml logs backend \
     | grep "Login successful" | grep "<attacker_ip>"
   ```
2. Check audit log for unexpected privilege changes or doctor verifications:
   ```sql
   SELECT timestamp, action, actor_id, ip_address 
   FROM audit_logs_auditlog 
   WHERE action IN ('USER_ROLE_CHANGED', 'DOCTOR_VERIFIED', 'CLINIC_APPROVED')
   ORDER BY timestamp DESC LIMIT 20;
   ```

### Resolution
1. For any accounts that suffered successful logins from the attacker IP, reset passwords and invalidate all active JWT refresh tokens:
   ```bash
   docker compose -f docker-compose.staging.yml exec backend python manage.py invalidate_user_sessions --email=<target_email>
   ```
2. Enforce mandatory email MFA verification for affected accounts.
3. Report incident to the security lead.

### Verification
- Verify attacking IP traffic is dropped (0 incoming requests in Nginx).
- Verify legitimate users can authenticate normally.

### Post-Incident Actions
- Adjust rate limits in Django REST Framework if thresholds were too lenient.
- Implement Cloudflare / WAF geo-blocking or managed challenge rules.

