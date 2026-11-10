# EazyDoc — Production Environment Separation & Architecture

This document defines the strict physical, logical, credential, and network isolation standards separating the **Production** environment from the **Staging** and **Development** environments of the EazyDoc multi-tenant healthcare platform.

---

## 1. Environment Isolation Philosophy

> [!CRITICAL]
> **Zero Shared State**: Under no circumstance shall a production system connect to a staging resource, nor shall a staging instance connect to production data stores, caches, or payment channels.

```
       +---------------------------------------------+
       |             STAGING ENVIRONMENT             |
       |  Host / Domain: staging.eazydoc.com         |
       |  Compose: docker-compose.staging.yml        |
       |  Env File: .env.staging                     |
       |  Database: eazydoc_staging_db               |
       |  Redis: eazydoc_redis_staging               |
       |  Razorpay: rzp_test_* (TEST MODE ONLY)      |
       |  Sentry: environment="staging"              |
       |  Email: Console / Mailpit sandbox           |
       +---------------------------------------------+
                              X  <--- STRICT ISOLATION / ZERO CROSS-TALK
       +---------------------------------------------+
       |            PRODUCTION ENVIRONMENT           |
       |  Host / Domain: eazydoc.com, api.eazydoc.com |
       |  Compose: docker-compose.prod.yml           |
       |  Env File: .env.production                  |
       |  Database: eazydoc_prod_db                  |
       |  Redis: eazydoc_redis_prod                  |
       |  Razorpay: rzp_live_* (LIVE - REQUIRES SIGN)|
       |  Sentry: environment="production"           |
       |  Email: Amazon SES / Verified SMTP          |
       +---------------------------------------------+
```

---

## 2. Component Separation Matrix

| Resource Dimension | Staging Configuration | Production Configuration | Isolation Mechanism |
| :--- | :--- | :--- | :--- |
| **Primary Domain** | `staging.eazydoc.com` | `eazydoc.com`, `www.eazydoc.com` | Distinct DNS records & TLS certs |
| **API Domain** | `staging.eazydoc.com/api/` | `api.eazydoc.com`, `/api/` | Distinct Nginx reverse proxy blocks |
| **PostgreSQL Database**| `eazydoc_staging_db` | `eazydoc_prod_db` | Separate container volume or RDS instance |
| **Database Credentials**| `eazydoc_staging_user` | `eazydoc_prod_user` | Independent cryptographic passwords |
| **Redis Broker & Cache**| `eazydoc_redis_staging` | `eazydoc_redis_prod` | Dedicated Redis container / ElastiCache |
| **Django SECRET_KEY** | Random 50+ chars (Staging) | Unique 64+ chars (Production) | Separate `.env` file |
| **Razorpay API Keys** | `rzp_test_*` | `rzp_live_*` | Test keys strictly rejected in production |
| **Razorpay Webhooks** | Staging Webhook Secret | Production Webhook Secret | Separate Razorpay Dashboard endpoints |
| **Media / Files Storage**| `staging_media_data` volume | Dedicated AWS S3 bucket (`eazydoc-prod-media`)| Dedicated IAM credentials & bucket ACL |
| **Error Tracking** | Sentry (`env="staging"`) | Sentry (`env="production"`) | Independent Sentry tags & sample rates |
| **Email Gateway** | Console / Mock backend | Verified Amazon SES SMTP | Prevents test emails reaching real patients|

---

## 3. Production Safeguards & Guardrails

### 3.1 Preventing Staging from Accessing Production Services
1. **Network Boundary**: Staging containers are hosted on isolated Docker bridge networks (`staging_internal_network`), physically separated from production networks (`internal_network`).
2. **Database Hardening**: Production PostgreSQL accepts connections strictly from authorized backend VPC subnets or the internal Docker network. Port 5432 is never bound to the public host interface (`0.0.0.0`).
3. **Razorpay Key Guard**:
   - In `backend/apps/payments/services.py`, payment initiation strictly verifies that test keys (`rzp_test_`) are NOT used when `ENVIRONMENT=production`.
   - Live keys (`rzp_live_`) are prohibited in staging settings.

### 3.2 Preventing Production from Accidental Dev/Staging Fallbacks
1. **No Hardcoded Secrets**: Django's `config.settings.production` raises a `django.core.exceptions.ImproperlyConfigured` exception if `SECRET_KEY` is empty, contains `"insecure"`, or matches development defaults.
2. **Explicit Environment Files**:
   - Staging uses `docker compose -f docker-compose.staging.yml --env-file .env.staging`.
   - Production uses `docker compose -f docker-compose.prod.yml --env-file .env.production`.
   - Default fallback to `.env` is disabled via explicit `${ENV_FILE}` bindings.
3. **Database Guard**: Production database migration scripts refuse to execute if `DATABASE_NAME` contains `"test"` or `"staging"`.

---

## 4. Production Secret Management Protocol

1. **Storage of Live Secrets**:
   - Live secrets must NEVER be committed to Git repositories or baked into Docker container layers.
   - On bare metal / EC2: `.env.production` is provisioned via AWS Systems Manager Parameter Store or HashiCorp Vault during instance bootstrapping with file permissions `0600` owned by `root:root` or `appuser:appuser`.
2. **Secret Rotation Policy**:
   - `SECRET_KEY`: Rotated annually or following any confirmed credentials exposure.
   - `DATABASE_PASSWORD`: Rotated bi-annually.
   - Razorpay API & Webhook Secrets: Rotated immediately via Razorpay dashboard with 24-hour dual-secret overlap if compromise is suspected.
   - JWT Signing Keys: Enforced 7-day token refresh lifecycle minimizes token exposure window.

