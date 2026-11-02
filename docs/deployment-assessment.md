# Staging Deployment Assessment

**Project:** EazyDoc Multi-Tenant Doctor Booking SaaS  
**Assessment Date:** 02 November 2026  
**Auditor / Role:** Senior DevOps Engineer, Django Architect, and React Deployment Specialist  
**Status:** **`APPROVED FOR STAGING RELEASE`**

---

## 1. Executive Summary

This assessment evaluates the readiness of the EazyDoc SaaS platform for deployment to a dedicated **Staging Environment**. The assessment encompasses application code, container definitions, database migrations, security configurations, network isolation, background workers, reverse proxy configurations, and automated testing.

Prior to this assessment, a comprehensive production-readiness audit (Day 15) resolved 10 critical security, isolation, and architectural vulnerabilities. All **311 backend automated tests** pass with 0 errors and 0 failures, and the React 19 frontend compiles cleanly with 0 lint warnings.

---

## 2. Current Infrastructure Overview

| Tier | Component | Technology / Version | Deployment Mode |
|---|---|---|---|
| **Edge / Proxy** | Reverse Proxy & SSL | Nginx 1.27 Alpine | Docker Container (`eazydoc_nginx_staging`) |
| **Frontend** | Single Page Application (SPA) | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui | Multi-stage Docker build + Alpine Nginx (`eazydoc_frontend_staging`) |
| **Backend API** | REST API & WebSockets | Python 3.13, Django 5.1, DRF 3.15, Daphne 4.1 (ASGI) | Docker Container (`eazydoc_backend_staging`) |
| **Database** | Relational Database | PostgreSQL 16 Alpine | Docker Container (`eazydoc_db_staging`) |
| **Message Broker** | Cache & Celery Queue | Redis 7 Alpine | Docker Container (`eazydoc_redis_staging`) |
| **Async Workers** | Background Task Processing | Celery 5.4 | Docker Container (`eazydoc_celery_staging`) |
| **Periodic Scheduler** | Cron / Reminder Scheduler | Celery Beat 2.7 (DatabaseScheduler) | Docker Container (`eazydoc_celery_beat_staging`) |
| **Payment Gateway** | Hosted Checkout & Webhooks | Razorpay Test Mode | Server-side signature & HMAC verification |

---

## 3. Existing Deployment Configuration Review

### 3.1 Docker & Compose Architecture
- **Development Compose (`docker-compose.yml`):** Configured for local development with volumes mounted to host source code, debug server, and ports bound to `127.0.0.1`.
- **Production Compose (`docker-compose.prod.yml`):** Production-ready topology utilizing Daphne ASGI, internal-only networks for database and Redis, and Nginx reverse proxy.
- **Staging Compose (`docker-compose.staging.yml`):** Dedicated staging configuration isolating staging volumes (`staging_postgres_data`, `staging_redis_data`, `staging_media_data`, `staging_staticfiles_data`), pointing to `.env.staging`, and binding to configurable staging host ports (80/443).

### 3.2 Backend Container Configuration (`backend/Dockerfile.prod`, `backend/entrypoint.sh`)
- Uses Python 3.13-slim.
- Non-root user execution (`appuser`, UID 1000).
- Multi-step entrypoint script with native Python socket connection polling to ensure PostgreSQL is fully accepting connections before running migrations or starting Daphne.
- Integrated `RUN_MIGRATIONS=true` and `COLLECT_STATIC=true` flags.

### 3.3 Frontend Container Configuration (`frontend/Dockerfile.prod`, `frontend/nginx.conf`)
- Multi-stage build (Node 22 builder stage compiles assets via `npm ci && npm run build`, followed by Nginx 1.27 Alpine serving `/dist`).
- SPA fallback routing: `try_files $uri $uri/ /index.html;` ensures React Router client-side routes load correctly upon direct URL access or browser refresh.
- Cache-control optimization: Immutable 1-year caching on `/assets/`, and `no-cache` on `/index.html`.

---

## 4. Assessment of Gaps & Remediations Identified

During the initial staging inspection, several configuration gaps were identified and remediated:

| Area | Finding / Gap | Severity | Remediation Action Taken |
|---|---|---|---|
| **Django Settings** | Missing dedicated `staging.py` settings module | **High** | Created `backend/config/settings/staging.py` inheriting from `base.py` with `DEBUG=False`, safe staging email backend, and Razorpay test-mode safety guards. |
| **CSRF Security** | Missing `CSRF_TRUSTED_ORIGINS` in Django settings | **High** | Configured `CSRF_TRUSTED_ORIGINS` across `base.py`, `staging.py`, and `production.py` to prevent 403 Forbidden errors on cross-origin requests. |
| **Frontend API URL** | Hardcoded `http://localhost:8000/api/v1` fallback in `frontend/src/services/api.ts` | **Medium** | Changed default to relative path `/api/v1`, allowing the frontend to dynamically proxy through Nginx in staging without hardcoding localhost. |
| **Entrypoint Packaging** | `docker/entrypoint.sh` was not included in `backend/` build context | **Medium** | Added `backend/entrypoint.sh`, granted execution permissions, and wired `ENTRYPOINT ["/app/entrypoint.sh"]` in `backend/Dockerfile.prod`. |
| **Static Assets** | Django Admin and Swagger UI staticfiles were unmapped in Nginx reverse proxy | **Medium** | Created shared volume `staging_staticfiles_data` and mapped `location /static/` in `docker/nginx/nginx.staging.conf`. |
| **HTTPS Support** | Missing SSL configuration and certificates for staging HTTPS testing | **Medium** | Added SSL server block on port 443 in `nginx.staging.conf` and implemented `scripts/generate_staging_certs.py` (and `.ps1`/`.sh`). |
| **Live Key Guard** | Risk of accidental live Razorpay key injection in staging | **High** | Added hard runtime assertion in `staging.py` raising an exception if `RAZORPAY_KEY_ID` begins with `rzp_live_`. |

---

## 5. Security and Tenant Isolation Assessment

1. **Role-Based Access Control (RBAC):**  
   All 5 platform roles (Patient, Doctor, Clinic Owner, Staff, Super Admin) have verified permission boundaries. Object-level permissions prevent horizontal privilege escalation (e.g. Clinic A cannot view Clinic B appointments or financial records).
2. **Network Isolation:**  
   PostgreSQL and Redis containers are attached strictly to `staging_internal_network` with no published host ports. Only Nginx publishes external ports (80 and 443).
3. **Session & Cookie Security:**  
   JWT authentication uses secure HttpOnly cookies (`access_token`, `refresh_token`). Refresh tokens rotate upon consumption, and invalidated tokens are blacklisted in Redis/DB.
4. **Secret Storage:**  
   No plaintext credentials exist in version control. Staging credentials must be supplied via `.env.staging` (derived from `.env.staging.example`) or CI/CD secret injection.

---

## 6. Deployment Blockers Analysis

| Potential Blocker | Assessment Result | Resolution |
|---|---|---|
| **Unresolved Critical Security Flaws** | **None** | All Day 15 audit findings remediated; 311 tests passing. |
| **Unapplied Database Migrations** | **None** | `makemigrations --check --dry-run` reports no schema differences. |
| **Failing Automated Tests** | **None** | 311 backend tests passing (including 6 E2E staging verification tests). |
| **Frontend Compilation Errors** | **None** | `npm run lint` and `npm run build` pass with 0 errors and 0 warnings. |
| **Domain / DNS Dependency** | **Resolved** | Staging Nginx supports `localhost`, `127.0.0.1`, and `staging.eazydoc.internal` via local hosts file or DNS. |

---

## 7. Recommended Staging Architecture & Launch Steps

1. **Host Environment:** Linux (Ubuntu 22.04 LTS / 24.04 LTS) or Windows Server running Docker Engine 26+ and Docker Compose v2.
2. **Configuration File:** `.env.staging` generated from `.env.staging.example` with random `SECRET_KEY` and staging database password.
3. **Certificate Generation:** Run `python scripts/generate_staging_certs.py` to create self-signed SSL certificates for `staging.eazydoc.internal`.
4. **Service Startup:**
   ```bash
   docker compose -f docker-compose.staging.yml up -d --build
   ```
5. **Health Verification:**
   ```bash
   python scripts/staging_health_check.py http://localhost
   ```

