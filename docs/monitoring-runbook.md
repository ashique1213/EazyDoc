# EazyDoc — SRE & Operations Monitoring Runbook

This runbook defines the daily and weekly operational checklists, triage procedures, diagnostic tool commands, and escalation contacts for the EazyDoc Site Reliability and DevOps team.

---

## 1. Daily Operations Checklist (Morning Shift — 09:00 Local)

Conduct this 5-minute sanity check every weekday morning:

- [ ] **Check Super Admin Operations Dashboard**:
  Access `https://staging.eazydoc.com/api/v1/admin/dashboard/operations/` (or via Admin Web UI):
  - Verify `system_health.database.status == "ok"` (latency < 2ms).
  - Verify `system_health.redis.status == "ok"` (latency < 5ms).
  - Verify `system_health.celery.status == "healthy"` (at least 1 active worker).
  - Check `active_warnings` array is empty (`[]`).
- [ ] **Verify Backup Freshness**:
  - In the operations dashboard, verify `backup_status.status == "healthy"` and `backup_status.age_hours < 26`.
- [ ] **Review Sentry Unresolved Issues**:
  - Open Sentry project `eazydoc-staging`.
  - Triage any new unhandled exceptions from the last 24 hours.
- [ ] **Inspect Reminder & Notification Deliveries**:
  - In the operations dashboard, ensure `overdue_pending_reminders == 0` and `notifications.failed` is within acceptable tolerance (< 2%).

---

## 2. Weekly Maintenance Checklist (Every Monday)

- [ ] **PostgreSQL Cache & Index Hit Ratios**:
  Run diagnostic SQL in `docs/database-monitoring.md`:
  - Ensure Buffer Cache Hit Ratio > 99%.
  - Verify table dead tuple bloat is < 15%.
- [ ] **Disk Space Verification**:
  ```bash
  docker compose -f docker-compose.staging.yml exec backend df -h /app
  ```
  Ensure free disk space exceeds 25%.
- [ ] **Docker System Prune**:
  Clean up dangling images and stopped test containers:
  ```bash
  docker system prune -f --volumes=false
  ```
- [ ] **Audit Log Inspection**:
  Verify zero unauthorized role escalations or suspicious cross-tenant attempts.

---

## 3. Quick Diagnostic Cheatsheet

### 3.1 Check Live Container Health & Logs
```bash
# Check container status
docker compose -f docker-compose.staging.yml ps

# Check backend logs
docker compose -f docker-compose.staging.yml logs --tail=100 -f backend

# Check Celery logs
docker compose -f docker-compose.staging.yml logs --tail=100 -f celery

# Trace a specific Request ID
docker compose -f docker-compose.staging.yml logs backend | grep "req_<trace_id>"
```

### 3.2 Health Check Direct Probes
```bash
# Liveness (Does not hit DB, tests ASGI process)
curl -i http://localhost:8000/api/v1/health/live/

# Readiness (Checks DB and Redis connectivity)
curl -i http://localhost:8000/api/v1/health/ready/
```

### 3.3 Redis & Celery Status Commands
```bash
# Ping Redis
docker compose -f docker-compose.staging.yml exec redis redis-cli ping

# Check Celery Queue Backlog
docker compose -f docker-compose.staging.yml exec redis redis-cli LLEN celery

# Ping Celery Workers
docker compose -f docker-compose.staging.yml exec celery celery -A config inspect ping
```

---

## 4. Incident Escalation Matrix & Contacts

| Role | Contact Channel | Primary Responsibility |
| :--- | :--- | :--- |
| **Primary On-Call SRE** | PagerDuty Schedule / Slack `@oncall-sre` | First responder for P1 / P2 alerts; initial triage within 15 mins |
| **Lead DevOps Engineer**| Slack `@devops-lead` / Phone | Escalation for infrastructure outages, network blocks, or host disk failures |
| **Backend Architect** | Slack `@django-architect` | Complex database locks, race conditions, ORM query degradation |
| **Security Officer** | Slack `#security-emergency` | Data leaks, suspicious authentication floods, credential rotation |

---

## 5. Incident Post-Mortem Template

Following resolution of any P1 or P2 incident, complete an incident post-mortem within 48 hours:

```markdown
# Incident Post-Mortem: [INC-YEAR-NUMBER] - [Brief Title]

**Date & Time**: YYYY-MM-DD HH:MM UTC  
**Duration**: XX minutes  
**Severity**: P1 / P2  
**Incident Commander**: [Name]  

### 1. Summary
Brief non-technical description of the incident and impact on users/clinics.

### 2. Timeline (UTC)
- **HH:MM** - Anomaly detected via [Alert / Sentry / User Report].
- **HH:MM** - On-call engineer acknowledged incident and began triage.
- **HH:MM** - Root cause identified as [X].
- **HH:MM** - Mitigation deployed: [Action].
- **HH:MM** - Full service recovery verified via health check probes.

### 3. Root Cause
Detailed explanation of why the failure occurred (5 Whys methodology).

### 4. Corrective & Preventive Actions
- [ ] [Action 1: Fix bug / improve query] (Owner: [Name], Due: YYYY-MM-DD)
- [ ] [Action 2: Update monitoring alert / runbook] (Owner: [Name], Due: YYYY-MM-DD)
```

