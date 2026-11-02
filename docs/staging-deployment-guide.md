# EazyDoc Staging Deployment Guide

This guide provides end-to-end instructions for deploying the EazyDoc Multi-Tenant Doctor Booking SaaS platform to a dedicated **Staging Environment**.

---

## 1. Staging Architecture Overview

The staging environment mirrors production architecture while strictly isolating data, credentials, and network boundaries:

```
[ Internet / Test Clients ]
           │
           ▼
[ Nginx Reverse Proxy (Ports 80 & 443) ]
     │                │                 │
     ▼                ▼                 ▼
[ React SPA ]   [ Daphne ASGI ]   [ Media & Static Volumes ]
(Frontend:80)   (Backend:8000)
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
     [ PostgreSQL 16 ]     [ Redis 7 ]
                             │      │
            ┌────────────────┘      └───────────────┐
            ▼                                       ▼
     [ Celery Worker ]                     [ Celery Beat ]
   (Async Tasks & Reminders)             (DatabaseScheduler)
```

**Key Isolation Principles:**
- PostgreSQL and Redis containers do NOT expose ports to the public internet; they communicate strictly over the internal bridge network `staging_internal_network`.
- Database data and cache states are stored in isolated Docker volumes: `staging_postgres_data` and `staging_redis_data`.
- Nginx terminates SSL/TLS and proxies requests to Daphne ASGI (`/api/`, `/admin/`, `/ws/`) and React SPA (`/`).

---

## 2. Prerequisites

Before deploying, ensure the host machine or virtual server meets the following requirements:
- **Operating System:** Linux (Ubuntu 22.04 LTS / 24.04 LTS recommended) or Windows Server / Windows 11 with WSL2.
- **Docker Engine:** Version 24.0+ (Docker Compose v2.20+).
- **RAM:** Minimum 4 GB (8 GB recommended for concurrent builds and workers).
- **Disk Space:** Minimum 20 GB free disk space.
- **Python:** Python 3.11+ installed on host (for helper scripts, optional if using Docker directly).

---

## 3. Step-by-Step Staging Setup

### Step 3.1: Clone the Codebase
```bash
git clone https://github.com/ashique1213/EazyDoc.git
cd EazyDoc
git checkout develop  # Or the release staging branch
```

### Step 3.2: Configure Staging Environment Variables
Copy the template file to `.env.staging`:
```bash
cp .env.staging.example .env.staging
```
Edit `.env.staging` and update the required values:
- Generate a secure `SECRET_KEY` (minimum 50 random characters):
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
- Set a strong `DATABASE_PASSWORD`.
- Configure Razorpay test credentials (`rzp_test_*`).
- Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to include your staging domain or IP.

> [!WARNING]
> Never use live Razorpay keys (`rzp_live_*`) in staging. The staging settings module will automatically abort execution if live keys are detected.

### Step 3.3: Generate Staging SSL Certificates
For local or internal staging testing, generate self-signed SSL certificates for `staging.eazydoc.internal`:

**Using Python (Platform-Independent):**
```bash
python scripts/generate_staging_certs.py
```

**Using PowerShell (Windows):**
```powershell
.\scripts\generate_staging_certs.ps1
```

**Using Bash (Linux/macOS):**
```bash
chmod +x scripts/generate_staging_certs.sh
./scripts/generate_staging_certs.sh
```
This places `staging.crt` and `staging.key` in `docker/nginx/certs/`, which are mounted as read-only by the Nginx container.

### Step 3.4: Build and Start Containers
Launch all staging services in detached mode:
```bash
docker compose -f docker-compose.staging.yml up -d --build
```

### Step 3.5: Monitor Container Startup & Healthchecks
Check container statuses:
```bash
docker compose -f docker-compose.staging.yml ps
```
Expected output:
- `eazydoc_db_staging` (healthy)
- `eazydoc_redis_staging` (healthy)
- `eazydoc_backend_staging` (healthy)
- `eazydoc_celery_staging` (running)
- `eazydoc_celery_beat_staging` (running)
- `eazydoc_frontend_staging` (running)
- `eazydoc_nginx_staging` (running, ports 80 and 443 forwarded)

View real-time logs:
```bash
docker compose -f docker-compose.staging.yml logs -f backend
```

### Step 3.6: Verify Database Migrations & Create Initial Super Admin
Migrations are applied automatically by `backend/entrypoint.sh` upon startup. To verify or create an administrative account, run:
```bash
docker compose -f docker-compose.staging.yml exec backend python manage.py createsuperuser
```
Follow the interactive prompts to set an email and password.

---

## 4. Domain & DNS Configuration

### 4.1 Local / Internal Testing via Hosts File
To access the staging environment at `https://staging.eazydoc.internal`:
- **Linux / macOS:** Add to `/etc/hosts`:
  ```text
  127.0.0.1 staging.eazydoc.internal
  ```
- **Windows:** Add to `C:\Windows\System32\drivers\etc\hosts` (run Notepad as Administrator):
  ```text
  127.0.0.1 staging.eazydoc.internal
  ```
Open `https://staging.eazydoc.internal` in your browser. (Accept the self-signed certificate warning for testing).

### 4.2 Public / Staging Server DNS & Let's Encrypt (Production Staging)
When deploying to a public server (e.g. AWS EC2, DigitalOcean, Hetzner):
1. **DNS A Record:** Point `staging.eazydoc.com` to your staging server's public IP address.
2. **Firewall / Security Group:** Open ports `80` (HTTP) and `443` (HTTPS) inbound. Keep ports `5432` and `6379` closed.
3. **Certbot Let's Encrypt Integration:**
   Obtain a free SSL certificate:
   ```bash
   certbot certonly --webroot -w /var/www/certbot -d staging.eazydoc.com
   ```
   Map the Let's Encrypt certificates to `/etc/nginx/certs/staging.crt` and `/etc/nginx/certs/staging.key` in `docker-compose.staging.yml`.

---

## 5. Post-Deployment Operational Verification

Execute the staging automated operational healthcheck:
```bash
python scripts/staging_health_check.py http://localhost
```
Or in PowerShell:
```powershell
.\scripts\staging_health_check.ps1 -BaseUrl "http://localhost"
```

Verify the following core endpoints:
- **System Health:** `GET /api/v1/health/` -> Status 200 `{"status": "ok", "database": "ok", "redis": "ok"}`
- **OpenAPI Documentation:** `GET /api/docs/` -> Interactive Swagger UI renders
- **Frontend Application:** `GET /` -> React application loads with clinic/doctor discovery
- **Django Administration:** `GET /admin/` -> Admin login screen

---

## 6. Staging Maintenance & Common Commands

| Action | Command |
|---|---|
| **View All Container Logs** | `docker compose -f docker-compose.staging.yml logs -f` |
| **Inspect Backend Logs** | `docker compose -f docker-compose.staging.yml logs -f backend` |
| **Inspect Celery Worker Logs**| `docker compose -f docker-compose.staging.yml logs -f celery` |
| **Inspect Beat Logs** | `docker compose -f docker-compose.staging.yml logs -f celery-beat` |
| **Restart Backend Service** | `docker compose -f docker-compose.staging.yml restart backend` |
| **Stop All Services** | `docker compose -f docker-compose.staging.yml down` |
| **Stop & Purge Volumes (Reset)**| `docker compose -f docker-compose.staging.yml down -v` |
| **Backup Staging Database** | `.\scripts\backup_db.ps1` or `./scripts/backup_db.sh` |
| **Restore Staging Database**| `.\scripts\restore_db.ps1 -BackupFile <path>` |

