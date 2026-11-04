# EazyDoc — Celery & Background Job Monitoring Guide

This document outlines the observability, task duration telemetry, failure alerting, and scaling strategies for Celery workers and Celery Beat in EazyDoc.

---

## 1. Celery Architecture & Telemetry Pipeline

EazyDoc relies on Celery for asynchronous operations, including transactional emails, SMS reminders, payment webhook reconciliation, and daily digest reports.

```
+--------------------+        +-----------------------+        +----------------------+
| Django REST API    |        | Redis Broker          |        | Celery Workers       |
| Task Dispatcher    | -----> | (Queue: `celery`)     | -----> | (Concurrency: 2)     |
| (Attaches trace ID)|        | Redis DB 0            |        | Signal Instrumentation|
+--------------------+        +-----------------------+        +----------------------+
                                                                          |
                                                      +-------------------+-------------------+
                                                      |                                       |
                                                      v                                       v
                                          +-----------------------+               +-----------------------+
                                          | Structured Log Event  |               | Metrics & Failures    |
                                          | (duration_ms, status) |               | (Sentry Scrubber)     |
                                          +-----------------------+               +-----------------------+
```

---

## 2. Key Worker & Queue Metrics

| Metric | Target | Warning Threshold | Critical Alert | Health Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Ping / Heartbeat** | Active | 1 worker offline | 0 active workers | Background processing completely halted |
| **Queue Backlog (`celery`)** | < 10 tasks | > 50 tasks | > 200 tasks | Delayed patient confirmation and reminders |
| **Task Execution Time** | < 500 ms | > 2000 ms | > 10000 ms | Worker thread saturation |
| **Task Failure Rate** | < 0.5% | > 2% | > 5% | External provider outage (Email/SMS/Razorpay) |
| **Overdue Reminders** | 0 overdue | > 25 overdue | > 100 overdue | Patients miss scheduled appointments |
| **Worker Memory (RSS)** | < 300 MB | > 600 MB | > 800 MB | Risk of container Out-Of-Memory (OOM) kill |

---

## 3. Signal Instrumentation & Duration Tracking

EazyDoc wires Celery signals in `backend/config/celery.py`:

```python
# Task Start: Binds correlation ID and starts timer
@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **_):
    req_id = kwargs.pop("request_id", None) or f"task_{task_id[:16]}"
    set_current_request_id(req_id)
    _task_start_times[task_id] = time.perf_counter()

# Task Completion: Calculates duration and emits structured log
@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, **_):
    start = _task_start_times.pop(task_id, None)
    duration_ms = round((time.perf_counter() - start) * 1000, 2) if start else 0.0
    logger.info(
        f"Celery task finished: {task.name} [{state}] in {duration_ms}ms",
        extra={"task_name": task.name, "task_id": task_id, "duration_ms": duration_ms, "state": state}
    )

# Task Failure: Logs scrubbed error and notifies Sentry
@task_failure.connect
def task_failure_handler(task_id, exception, traceback, **_):
    logger.error(
        f"Celery task failed: {task_id}: {exception}",
        exc_info=True,
        extra={"task_id": task_id}
    )
```

---

## 4. Operational Commands for Worker Inspection

### 4.1 Ping Active Workers via CLI
```bash
# Inside Celery container
celery -A config inspect ping

# Expected response:
# -> celery@eazydoc_celery_staging: OK
```

### 4.2 Inspect Active Running Tasks
```bash
celery -A config inspect active
```

### 4.3 Check Queue Length in Redis Directly
```bash
# Query the length of the default Celery queue in Redis
redis-cli -n 0 LLEN celery
```

### 4.4 Inspect Scheduled / Delayed Tasks
```bash
celery -A config inspect scheduled
```

---

## 5. Celery Worker Hardening Settings

EazyDoc applies the following settings in `backend/config/settings/base.py`:

```python
# Prevent tasks from hanging indefinitely
CELERY_TASK_TIME_LIMIT = 300       # Hard kill after 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # Soft exception after 4 minutes

# Fair task distribution (prevent 1 worker hoarding tasks)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Acknowledge task only AFTER execution finishes (resilience against worker crash)
CELERY_TASK_ACKS_LATE = True

# Max tasks per worker process before auto-recycling (prevents Python memory leaks)
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
```

---

## 6. Celery Beat Schedule Verification

Celery Beat triggers periodic cron schedules defined in `CELERY_BEAT_SCHEDULE`:

| Schedule Key | Interval | Purpose |
| :--- | :--- | :--- |
| `dispatch-appointment-reminders` | Every 5 minutes | Queries `AppointmentReminderSchedule` for due items |
| `reconcile-pending-payments` | Every 15 minutes | Verifies unconfirmed Razorpay transactions |
| `generate-daily-clinic-reports` | Daily at 01:00 UTC | Aggregates daily appointment and financial stats |

### Verifying Beat Health:
1. In the Super Admin dashboard (`/api/v1/admin/dashboard/operations/`), verify `overdue_pending_reminders` is near zero.
2. If `overdue_pending_reminders` increases continuously, Celery Beat or the reminder task worker has halted.

