# EazyDoc — Monitoring & Observability Architecture

This document details the end-to-end monitoring, logging, tracing, metrics, alerting, and operational visibility architecture for the EazyDoc multi-tenant doctor booking SaaS platform.

---

## 1. Observability Architecture Overview

The EazyDoc observability model adheres to the **Three Pillars of Observability** (Metrics, Logs, and Traces), augmented with **Multi-Tenant Health Checks** and **Automated Incident Response**.

```
                           +-------------------------------------+
                           |            Browser / Client         |
                           |  (React SPA + ErrorBoundary + Vite) |
                           +-------------------------------------+
                                              |
                                              | HTTPS / WSS
                                              | X-Request-ID Header
                                              v
                           +-------------------------------------+
                           |            Nginx Proxy              |
                           |   - Generates/Propagates Request ID |
                           |   - Rate Limiting / SSL Termination |
                           |   - /health/live & /health/ready    |
                           +-------------------------------------+
                                              |
                      +-----------------------+-----------------------+
                      |                                               |
                      v                                               v
        +---------------------------+                   +---------------------------+
        |   Django REST API Backend |                   |      Nginx Static/Media   |
        |  - RequestIDMiddleware    |                   |   - Direct Volume Cache   |
        |  - StructuredJSONLog      |                   +---------------------------+
        |  - Sensitive Data Scrubber|
        |  - Sentry SDK before_send |
        +---------------------------+
                      |
         +------------+------------+-----------------------+
         |                         |                       |
         v                         v                       v
+------------------+      +------------------+    +-------------------+
| PostgreSQL 16 DB |      | Redis 7 Broker   |    | Celery Workers &  |
| - Connection Pool|      | - Cache / Sessions|   | Celery Beat Engine|
| - Latency Probes |      | - Celery Queues  |    | - Correlated ID   |
| - Backup Verify  |      | - Memory Alerts  |    | - Task Duration ms|
+------------------+      +------------------+    +-------------------+
         ^                         ^                       ^
         |                         |                       |
         +-------------------------+-----------------------+
                                   |
                                   v
             +-------------------------------------------+
             | Super Admin Operations Dashboard Endpoint |
             |    `GET /api/v1/admin/dashboard/operations/|
             | - DB/Redis Latency (ms)                   |
             | - Celery Worker Heartbeat & Queues        |
             | - 24-Hour Business & Payment Metrics      |
             | - Active Warnings & Backup Status         |
             +-------------------------------------------+
```

---

## 2. Telemetry Flow & Request Correlation

### 2.1 Correlation Lifecycle (`X-Request-ID`)
1. **Client Ingress**: If a client provides an `X-Request-ID` or `X-Correlation-ID`, Nginx and Django inspect it. If missing, Nginx (`$request_id`) or Django's `RequestIDMiddleware` generates a cryptographic UUID prefixed with `req_`.
2. **Middleware Sanitization**: `RequestIDMiddleware` validates the correlation token against `^[a-zA-Z0-9_\-]{8,64}$` to eliminate header injection attacks.
3. **Execution Context**: The verified request ID is stored in Python's thread/async-safe `contextvars.ContextVar`.
4. **Structured Logging**: All Python loggers format records through `StructuredJSONFormatter`, which injects the `request_id` into every log event.
5. **Celery Worker Propagation**: When async background tasks are enqueued (e.g. notifications, reminder dispatch, commission payouts), the `request_id` is passed via task kwargs or `celery.signals.task_prerun`, binding async worker execution back to the originating HTTP transaction.
6. **Egress Headers**: Responses return `X-Request-ID` to the browser, allowing frontend error boundaries and support tickets to cite the exact trace ID.

---

## 3. Log Collection & Parsing Strategy

### 3.1 JSON Format Specification
Logs are streamed to `stdout` / `stderr` in standard NDJSON (Newline Delimited JSON) format:

```json
{
  "timestamp": "2026-11-04T08:15:20.120456Z",
  "level": "INFO",
  "app": "eazydoc",
  "environment": "staging",
  "request_id": "req_45ce1d3a4755487eb149232c0a0307e9",
  "logger": "apps.appointments",
  "module": "services",
  "line": 333,
  "message": "Appointment successfully booked: EZD-202611-8D9V78",
  "extra": {
    "booking_reference": "EZD-202611-8D9V78",
    "clinic_id": "97dee595-0453-468d-a38f-8afaed54f21a",
    "doctor_id": "5e3fb12f-e62a-4f95-92b1-bf4d766921e3",
    "payment_amount": "1500.00"
  }
}
```

### 3.2 Redaction & Scrubbing Pipeline
- **In-Memory Filtering**: `SensitiveDataFilter` and `redact_sensitive_data` intercept log dicts before emission.
- **Scrubbed Fields**: Passwords, auth tokens, refresh tokens, JWTs, Razorpay secrets/signatures, CVVs, PANs, and patient clinical notes.
- **Sentry Scrubber**: Staging and production configurations apply a `before_send` scrubber that strips HTTP cookies, Authorization headers, and sensitive POST request bodies before transmitting crash events to Sentry.

---

## 4. Metrics & Operational Instrumentation

| Metric Domain | Metric Name | Collector / Source | Alert Threshold | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **API Availability** | HTTP 5xx Error Rate | Nginx access logs / Sentry | > 5% over 5 mins | P1 (Critical) |
| **API Latency** | P95 Response Time | Nginx / Django middleware | > 2000 ms sustained | P2 (High) |
| **Database** | Active DB Connections | `pg_stat_activity` | > 85% max_connections | P1 (Critical) |
| **Database** | Query Execution Time | `pg_stat_statements` | Single query > 1000 ms | P3 (Medium) |
| **Cache & Broker** | Redis Memory Usage | `INFO memory` | > 85% maxmemory | P2 (High) |
| **Background Jobs** | Celery Worker Heartbeat | Celery Inspect / Ping | 0 active workers | P1 (Critical) |
| **Background Jobs** | Reminder Queue Backlog | `AppointmentReminderSchedule` | > 50 overdue items | P2 (High) |
| **Payments** | Webhook Failure Rate | `PaymentWebhookEvent` | > 10% failures in 1 hr | P1 (Critical) |
| **Storage** | Host Disk Utilization | Host / Docker Volume | > 85% full | P2 (High) |
| **Backups** | Backup Freshness | `pg_dump` timestamp | > 26 hours old | P1 (Critical) |

---

## 5. Alert Routing & Escalation Matrix

```
   Alert Generated (Sentry / Ops Check / Nginx 5xx / Webhook Failure)
                                   |
                +------------------+------------------+
                |                                     |
         Severity P1 / P2                      Severity P3 / P4
                |                                     |
     +--------------------+                 +--------------------+
     | PagerDuty / Opsgenie|                | Slack Alert Channel|
     | - On-Call Engineer  |                | - Daily Ops Triage |
     | - SMS + Call Alert  |                +--------------------+
     +--------------------+
                |
     Unacknowledged > 15m
                |
                v
     +--------------------+
     | Lead DevOps / SRE  |
     +--------------------+
```

---

## 6. Super Admin Operations Dashboard (`/api/v1/admin/dashboard/operations/`)

The platform includes a real-time operational dashboard endpoint accessible strictly to Super Administrators (`role=SUPER_ADMIN`).

### Sample Response Output:
```json
{
  "status": "success",
  "data": {
    "system_health": {
      "database": {
        "status": "ok",
        "latency_ms": 0.45
      },
      "redis": {
        "status": "ok",
        "latency_ms": 1.20
      },
      "celery": {
        "status": "healthy",
        "active_workers": ["celery@eazydoc-worker-1"]
      }
    },
    "business_operations_24h": {
      "appointments": {
        "total": 142,
        "confirmed": 118,
        "cancelled": 12,
        "rescheduled": 8,
        "completed": 4
      },
      "payments": {
        "total": 142,
        "successful": 138,
        "failed": 4,
        "pending": 0
      },
      "webhooks": {
        "total": 150,
        "processed": 148,
        "failed": 2,
        "received": 0
      },
      "notifications": {
        "total": 320,
        "sent": 315,
        "failed": 5,
        "processing": 0,
        "overdue_pending_reminders": 0
      }
    },
    "backup_status": {
      "status": "healthy",
      "latest_backup": "backup_eazydoc_staging_20261104_020000.sql.gz",
      "age_hours": 6.2,
      "size_bytes": 14205830
    },
    "active_warnings": []
  }
}
```

