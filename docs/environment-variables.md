# Environment Variables Reference

This document provides a comprehensive inventory of all environment variables used by the EazyDoc SaaS platform across **Development**, **Staging**, and **Production** environments.

---

## 1. Security & Storage Rules

> [!IMPORTANT]
> - **Never Commit Credentials:** `.env`, `.env.staging`, or `.env.production` files containing live secrets must NEVER be committed to Git.
> - **Secret Separation:** Frontend environment variables (prefixed with `VITE_`) are bundled into client-side JavaScript. **Never put backend secrets, database credentials, or private API keys into frontend variables.**
> - **Staging Test Isolation:** Staging environments must only use Razorpay test keys (`rzp_test_*`). Live keys (`rzp_live_*`) are blocked at startup.
> - **Production Guardrails:** Production requires `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, and a dedicated database.

---

## 2. Environment Comparison Matrix

| Variable Name | Development Default | Staging Default | Production Requirement |
|---|---|---|---|
| `DEBUG` | `True` | `False` | `False` (Mandatory) |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | `config.settings.staging` | `config.settings.production` |
| `SECRET_KEY` | Development key | 50+ char random staging key | 64+ char high-entropy cryptokey |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `staging.eazydoc.com` | `eazydoc.com,www.eazydoc.com,api.eazydoc.com` |
| `DATABASE_NAME` | `eazydoc_db` | `eazydoc_staging_db` | `eazydoc_prod_db` |
| `DATABASE_USER` | `eazydoc_user` | `eazydoc_staging_user` | `eazydoc_prod_user` |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | `redis://redis:6379/0` (Isolated DB) |
| `RAZORPAY_KEY_ID` | `rzp_test_*` | `rzp_test_*` | `rzp_live_*` (After human signoff) |
| `SECURE_SSL_REDIRECT` | `False` | `False` | `True` |
| `SESSION_COOKIE_SECURE`| `False` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `False` | `True` |
| `JWT_AUTH_COOKIE_SECURE`| `False` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `0` | `31536000` (1 Year) |
| `EMAIL_BACKEND` | `console.EmailBackend` | `console.EmailBackend` | `smtp.EmailBackend` (Amazon SES) |
| `LOG_FORMAT` | `verbose` | `json` | `json` |
| `SENTRY_ENVIRONMENT` | `development` | `staging` | `production` |

---

## 3. Detailed Variable Specifications

### 3.1 Core Application & Security

| Variable Name | Required | Type | Description & Constraints |
|---|---|---|---|
| `DEBUG` | Yes | Boolean | Must strictly be `False` in staging and production. |
| `DJANGO_SETTINGS_MODULE` | Yes | String | Python module path for settings (`config.settings.staging` or `config.settings.production`). |
| `SECRET_KEY` | Yes | String | Cryptographic signing key. Minimum 50 random characters. |
| `ALLOWED_HOSTS` | Yes | Comma-separated | Host/domain names Django can serve. |
| `CSRF_TRUSTED_ORIGINS` | Yes | Comma-separated | Trusted origins for CSRF protection on mutation requests. |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated | Client origins permitted for cross-origin API access. |

### 3.2 Network & SSL / Cookie Flags

| Variable Name | Required | Default | Description & Constraints |
|---|---|---|---|
| `PROD_HTTP_PORT` | No | `80` | Host port mapped to Nginx reverse proxy HTTP. |
| `PROD_HTTPS_PORT` | No | `443` | Host port mapped to Nginx reverse proxy HTTPS. |
| `SECURE_SSL_REDIRECT` | No | `True` in prod | Redirects HTTP traffic to HTTPS. |
| `SESSION_COOKIE_SECURE`| No | `True` in prod | Transmits session cookie over HTTPS only. |
| `CSRF_COOKIE_SECURE` | No | `True` in prod | Transmits CSRF cookie over HTTPS only. |
| `JWT_AUTH_COOKIE_SECURE`| No | `True` in prod | Transmits JWT HttpOnly cookies over HTTPS only. |
| `SECURE_HSTS_SECONDS` | No | `31536000` | HTTP Strict Transport Security duration. |

### 3.3 Database, Cache & Celery

| Variable Name | Required | Default | Description & Constraints |
|---|---|---|---|
| `DATABASE_NAME` | Yes | *e.g. eazydoc_prod_db*| PostgreSQL database name. |
| `DATABASE_USER` | Yes | *e.g. eazydoc_prod_user*| PostgreSQL username. |
| `DATABASE_PASSWORD` | Yes | *Secret* | PostgreSQL user password. |
| `DATABASE_HOST` | Yes | `db` | Database hostname (container name `db` or RDS endpoint). |
| `DATABASE_PORT` | No | `5432` | PostgreSQL listening port. |
| `CONN_MAX_AGE` | No | `60` | Persistent DB connection lifetime in seconds. |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection URL for caching and channels. |
| `CELERY_BROKER_URL` | Yes | `redis://redis:6379/0` | Celery message broker URI. |
| `CELERY_RESULT_BACKEND`| Yes | `redis://redis:6379/1` | Celery task result backend URI (database index 1). |

### 3.4 Razorpay Payment Gateway

| Variable Name | Required | Format | Description & Constraints |
|---|---|---|---|
| `RAZORPAY_KEY_ID` | Yes | `rzp_test_*` or `rzp_live_*` | Razorpay public key ID. |
| `RAZORPAY_KEY_SECRET` | Yes | String | Razorpay API secret key for HMAC signature verification. |
| `RAZORPAY_WEBHOOK_SECRET`| Yes| String | Secret key for verifying incoming webhook signatures. |
| `RAZORPAY_CURRENCY` | No | `INR` | ISO 4217 currency code. |

### 3.5 Storage & Observability

| Variable Name | Required | Default | Description & Constraints |
|---|---|---|---|
| `EMAIL_BACKEND` | No | `smtp.EmailBackend` | Django email backend implementation. |
| `EMAIL_HOST` | No | *SMTP host* | Hostname of SMTP mail server. |
| `DEFAULT_FROM_EMAIL` | No | `EazyDoc <noreply@eazydoc.com>`| Sender address for outgoing emails. |
| `SENTRY_DSN` | No | *Empty* | Sentry project DSN for error reporting. |
| `AWS_STORAGE_BUCKET_NAME`| No | *Bucket name* | S3 bucket for uploaded medical documents and media. |
| `AWS_S3_REGION_NAME` | No | `ap-south-1` | AWS S3 region (Mumbai). |

---

## 4. Frontend Environment Variables (`frontend/.env.production`)

| Variable Name | Required | Production Value | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `/api/v1` | Relative API path behind Nginx reverse proxy. |
| `VITE_APP_ENV` | No | `production` | Environment indicator. |
