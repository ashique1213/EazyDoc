# EazyDoc — Performance Baselines & Latency Targets

This document establishes the official performance benchmarks, latency SLOs, and resource utilization baselines for the EazyDoc multi-tenant doctor booking SaaS.

---

## 1. API Latency Service Level Objectives (SLOs)

| Endpoint Category | Method & Route | P50 (Target) | P95 (Warning) | P99 (Critical) | Max Permitted |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **System Liveness** | `GET /api/v1/health/live/` | 5 ms | 15 ms | 30 ms | 100 ms |
| **System Readiness** | `GET /api/v1/health/ready/` | 15 ms | 45 ms | 90 ms | 250 ms |
| **Authentication** | `POST /api/v1/auth/login/` | 120 ms | 250 ms | 450 ms | 1,000 ms |
| **Token Refresh** | `POST /api/v1/auth/refresh/` | 25 ms | 60 ms | 120 ms | 300 ms |
| **Public Clinic Directory**| `GET /api/v1/public/clinics/` | 40 ms | 110 ms | 220 ms | 500 ms |
| **Doctor Availability Slots**| `GET /api/v1/public/doctors/{id}/slots/` | 35 ms | 90 ms | 180 ms | 400 ms |
| **Appointment Booking** | `POST /api/v1/appointments/` | 85 ms | 220 ms | 400 ms | 1,200 ms |
| **Payment Order Creation**| `POST /api/v1/payments/create-order/` | 140 ms | 350 ms | 700 ms | 2,000 ms |
| **Razorpay Webhook** | `POST /api/v1/payments/webhook/` | 45 ms | 120 ms | 250 ms | 800 ms |
| **Super Admin Operations**| `GET /api/v1/admin/dashboard/operations/`| 50 ms | 150 ms | 300 ms | 800 ms |

---

## 2. Background Job Performance Baselines

| Job Name | Trigger | Target Execution Time | Max Permitted | Retries Permitted |
| :--- | :--- | :--- | :--- | :--- |
| `send_email_notification_task` | Event-driven (Celery) | < 1,500 ms | 5,000 ms | 3 |
| `dispatch_appointment_reminders` | Periodic (Every 5 mins) | < 800 ms | 3,000 ms | 1 |
| `reconcile_pending_payments` | Periodic (Every 15 mins) | < 1,200 ms | 5,000 ms | 2 |
| `generate_daily_clinic_reports` | Daily (01:00 UTC) | < 15,000 ms | 60,000 ms | 2 |

---

## 3. Resource Utilization Baselines (Staging & Production)

### 3.1 Backend Daphne Containers
- **Idle CPU**: < 2%
- **Under Normal Load (50 req/s)**: < 25% CPU per container
- **Idle Memory (RSS)**: ~85 MB
- **Peak Memory (Under Load)**: < 250 MB
- **Container Memory Limit**: 512 MB (triggers alert at 80% / 410 MB)

### 3.2 Celery Worker Containers
- **Idle CPU**: < 1%
- **Peak CPU (Batch notification dispatch)**: < 40% CPU
- **Memory Footprint**: ~110 MB (Recycled automatically after 1,000 tasks via `CELERY_WORKER_MAX_TASKS_PER_CHILD`)
- **Container Memory Limit**: 512 MB

### 3.3 PostgreSQL Database
- **Active Connections**: 10–25 connections (Target < 50 out of 100 max)
- **Buffer Cache Hit Ratio**: > 99.2%
- **Index Scan vs Sequential Scan**: > 98.5% index hits
- **Disk I/O Latency**: < 2 ms on SSD storage

### 3.4 Redis Cache & Broker
- **Key Count (Cache DB 1)**: ~5,000 keys
- **Queue Count (Celery DB 0)**: 0–10 items under steady state
- **Memory Consumption**: < 64 MB
- **Redis Memory Limit**: 256 MB with `maxmemory-policy allkeys-lru`

---

## 4. Performance Degradation Triggers

If any metric drifts into the following territory for longer than 3 minutes, an alert is triggered:
- P95 latency > 1,500 ms for any booking or authentication endpoint.
- PostgreSQL active connections > 75.
- Celery `overdue_pending_reminders` > 25.
- Redis memory usage > 180 MB.

