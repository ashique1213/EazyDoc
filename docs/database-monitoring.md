# EazyDoc — PostgreSQL Database Monitoring & Performance Guide

This document defines the metrics, query profiling techniques, diagnostic SQL queries, connection pool sizing, and maintenance procedures for the EazyDoc PostgreSQL database.

---

## 1. Key Metrics & Alert Thresholds

| Metric | Target / Healthy | Warning Threshold | Critical Alert | Metric Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Active Connections** | < 50% max | 75% max_connections | > 85% max_connections | Prevent connection starvation and 500 errors |
| **Cache Hit Ratio (Buffer)** | > 99% | < 95% | < 90% | Memory efficiency; low ratio indicates missing RAM/indices |
| **Index Hit Ratio** | > 98% | < 95% | < 90% | Missing indexes causing full table sequential scans |
| **Transaction Rollback Rate** | < 1% | > 3% | > 5% | Indicates serialization failures or constraint crashes |
| **Dead Tuples (Bloat)** | < 10% | > 20% table size | > 30% table size | Autovacuum lag degrading index traversal speed |
| **Long Running Queries** | 0 > 1s | Single query > 2s | Any query > 5s | Unoptimized JOINs, missing indexes, lock deadlocks |
| **Replication Lag** | < 100ms | > 5 seconds | > 30 seconds | Read-replica staleness |

---

## 2. Essential Diagnostic SQL Queries

DevOps and SRE engineers can execute these diagnostic queries directly in `psql` or through automated monitoring jobs:

### 2.1 Connection Saturation & State
```sql
SELECT 
    state,
    count(*) AS count,
    round(100.0 * count(*) / (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'), 2) AS pct_of_max
FROM pg_stat_activity
GROUP BY state
ORDER BY count DESC;
```

### 2.2 Buffer Cache Hit Ratio (Target: > 99%)
```sql
SELECT 
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit)  AS heap_hit,
    round(sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read) + 0.0001) * 100, 2) AS cache_hit_pct
FROM pg_statio_user_tables;
```

### 2.3 Index Hit Ratio (Target: > 98%)
```sql
SELECT 
    relname AS table_name,
    idx_scan,
    seq_scan,
    round(100.0 * idx_scan / (idx_scan + seq_scan + 0.0001), 2) AS idx_hit_pct
FROM pg_stat_user_tables
WHERE seq_scan + idx_scan > 500
ORDER BY idx_hit_pct ASC
LIMIT 15;
```

### 2.4 Identifying Active Slow Queries & Lock Blocking
```sql
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state,
    wait_event_type,
    wait_event
FROM pg_stat_activity
WHERE state != 'idle'
  AND (now() - pg_stat_activity.query_start) > interval '2 seconds'
ORDER BY duration DESC;
```

### 2.5 Dead Tuple Accumulation (Table Bloat)
```sql
SELECT 
    relname AS table_name,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    round(100.0 * n_dead_tup / (n_live_tup + n_dead_tup + 0.0001), 2) AS dead_tuple_pct,
    last_autovacuum,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
```

---

## 3. Query Performance Profiling with `pg_stat_statements`

The staging and production environments enable the PostgreSQL extension `pg_stat_statements` for execution frequency and runtime analysis.

### Top 5 Slowest Queries by Mean Time:
```sql
SELECT 
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(total_exec_time::numeric, 2) AS total_ms,
    calls,
    rows,
    substr(query, 1, 100) AS query_preview
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 5;
```

### Top 5 Most Frequent High-Volume Queries:
```sql
SELECT 
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(total_exec_time::numeric, 2) AS total_ms,
    substr(query, 1, 100) AS query_preview
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 5;
```

---

## 4. Connection Pool & Sizing Architecture

### 4.1 Django Database Connection Settings
- In staging/production:
  ```python
  # config/settings/production.py
  CONN_MAX_AGE = int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60"))
  ```
  This enables persistent connection reuse across HTTP requests for up to 60 seconds, reducing TCP/TLS handshake latency without locking connections indefinitely.

### 4.2 Pool Capacity Calculation Formula
For a staging/production server running Daphne / Celery:
$$\text{Max PostgreSQL Connections} = (\text{Daphne Worker Threads} \times N) + (\text{Celery Concurrency}) + \text{Superuser Buffer (10)}$$

- Daphne ASGI containers: 2 workers × 10 concurrent requests = ~20 connections
- Celery worker containers: 2 workers × 2 concurrency = 4 connections
- Celery Beat: 1 connection
- Admin / Migration Buffer: 10 connections
- **Total Peak Requirement**: ~35 connections.
- **Postgres `max_connections` configuration**: `100` (safe headroom).

---

## 5. Maintenance & Autovacuum Tuning

Autovacuum runs continuously in background to reclaim storage from updated appointments and logs.

Key PostgreSQL parameters in `postgresql.conf`:
- `autovacuum = on`
- `autovacuum_vacuum_scale_factor = 0.05` (triggers when 5% of rows are updated)
- `autovacuum_vacuum_threshold = 50`
- `autovacuum_vacuum_cost_limit = 1000` (prevents I/O spikes during business hours)

