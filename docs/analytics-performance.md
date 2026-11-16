# EazyDoc Analytics Performance & Query Optimization

This document details the database indexing strategy, query execution optimizations, caching architecture, and streaming export mechanics that ensure high-performance analytics across large multi-tenant datasets.

---

## 1. Database Indexing Strategy

To maintain sub-100ms response times on high-volume reporting queries, the database schema implements strategic indexes across all core models:

### `CommissionRecord` Indexes
- `(clinic, status)`: Fast lookup of clinic commissions by settlement state.
- `(appointment, status)`: Fast lookup of appointment revenue records.
- `(created_at)`: Accelerated date range boundary scans (`start_dt` to `end_dt`).

### `Payment` Indexes
- `(status)`: Filter for paid, failed, and refunded payments.
- `(clinic, status)`: Scoped financial queries per clinic.
- `(created_at)`: Time-series date partitioning.
- `(appointment, status)`: Payment reconciliation lookups.

### `Appointment` Indexes
- `(clinic, status)`: Clinic operational filtering.
- `(doctor, status)`: Practitioner workload and performance queries.
- `(start_at)`: Calendar slot queries and peak hour/day extraction.
- `(created_at)`: Booking creation timeline queries.

---

## 2. Query Optimization Patterns

### A. Single-Pass Aggregations
Instead of running separate queries for each metric or status count, the analytics service executes composite aggregations in a single database round-trip using Django's `Count` with conditional `Q` filters:
```python
appt_stats = appt_qs.aggregate(
    total=Count("id"),
    completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
    confirmed=Count("id", filter=Q(status=AppointmentStatus.CONFIRMED)),
    cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
    no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
    rescheduled=Count("id", filter=Q(reschedule_required=True)),
)
```

### B. Group By Date Series
Daily and monthly trend charts group rows directly in SQL:
```python
daily_payments = (
    pay_qs.values("created_at__date")
    .annotate(
        gross=Sum("amount", filter=Q(status=PaymentStatus.PAID)),
        paid_count=Count("id", filter=Q(status=PaymentStatus.PAID)),
        failed_count=Count("id", filter=Q(status=PaymentStatus.FAILED)),
    )
    .order_by("created_at__date")
)
```
This avoids fetching individual transaction rows into Python memory.

### C. Relationship Pre-fetching
When generating clinic comparison or doctor performance tables, related models are joined using `select_related`:
```python
Clinic.objects.all().select_related("owner")
DoctorClinic.objects.filter(clinic=clinic).select_related("doctor__user")
```
This guarantees an $O(1)$ query count regardless of the number of clinics or doctors.

---

## 3. Redis Cache Architecture

- **Engine**: Redis with fallback to in-memory caching during local testing.
- **TTL**: 180 seconds (3 minutes) default cache duration.
- **Key Determinism**: SHA-256 hash of sorted query parameters ensures consistent cache hits regardless of parameter ordering in query strings.
- **Bypass Capability**: Passing `?refresh=true` invalidates and overwrites stale cache entries with live data.

---

## 4. Export Memory Efficiency

Large CSV exports are streamed using standard Python `io.StringIO` buffers and chunked generator queries:
- Querysets utilize `iterator()` or targeted column projections (`values_list` / `select_related`) to prevent holding large querysets in memory simultaneously.
- UTF-8 BOM encoding ensures immediate, artifact-free opening in Microsoft Excel and Google Sheets.
