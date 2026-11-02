# Environment Variables Reference

This document provides a comprehensive inventory of all environment variables used by the EazyDoc SaaS platform across **Development**, **Staging**, and **Production** environments.

---

## 1. Security & Storage Rules

> [!IMPORTANT]
> - **Never Commit Credentials:** `.env`, `.env.staging`, or `.env.production` files containing live secrets must NEVER be committed to Git.
> - **Secret Separation:** Frontend environment variables (prefixed with `VITE_`) are bundled into client-side JavaScript. **Never put backend secrets, database credentials, or private API keys into frontend variables.**
> - **Staging Test Isolation:** Staging environments must only use Razorpay test keys (`rzp_test_*`). Live keys (`rzp_live_*`) are blocked at startup.

---

## 2. Backend Environment Variables (`.env.staging` / `.env`)

### 2.1 Core Application & Security

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `DEBUG` | Yes | `False` | Must strictly be `False` in staging and production. |
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.staging` | Python module path for settings (`config.settings.staging` or `config.settings.production`). |
| `SECRET_KEY` | Yes | *None (Must set)* | Cryptographic signing key. Minimum 50 random alphanumeric characters. |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1,staging.eazydoc.internal` | Comma-separated list of host/domain names Django can serve. |
| `CSRF_TRUSTED_ORIGINS` | Yes | `http://localhost,https://localhost,https://staging.eazydoc.internal` | Comma-separated list of trusted origins for CSRF protection on POST/PUT/DELETE requests. |
| `CORS_ALLOWED_ORIGINS` | Yes | `http://localhost,https://localhost,https://staging.eazydoc.internal` | Comma-separated list of client origins permitted to make cross-origin requests. |

### 2.2 Network & SSL / Cookie Flags

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `STAGING_HTTP_PORT` | No | `80` | Host port mapped to Nginx reverse proxy HTTP. |
| `STAGING_HTTPS_PORT` | No | `443` | Host port mapped to Nginx reverse proxy HTTPS. |
| `SECURE_SSL_REDIRECT` | No | `False` | Redirects all HTTP traffic to HTTPS inside Django. Set to `False` if Nginx or ALB handles TLS. |
| `SESSION_COOKIE_SECURE`| No | `False` | Marks session cookie with `Secure` flag (requires HTTPS). Set `True` if testing full HTTPS. |
| `CSRF_COOKIE_SECURE` | No | `False` | Marks CSRF cookie with `Secure` flag (requires HTTPS). Set `True` if testing full HTTPS. |
| `JWT_AUTH_COOKIE_SECURE`| No | `False` | Marks JWT HttpOnly cookies with `Secure` flag. Set `True` when served over HTTPS. |
| `SECURE_HSTS_SECONDS` | No | `0` | HTTP Strict Transport Security seconds. Keep `0` in staging to avoid browser caching issues. |

### 2.3 PostgreSQL Database

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `DATABASE_NAME` | Yes | `eazydoc_staging_db` | Name of the PostgreSQL database. |
| `DATABASE_USER` | Yes | `eazydoc_staging_user` | PostgreSQL database username. |
| `DATABASE_PASSWORD` | Yes | *None (Must set)* | Password for PostgreSQL user. |
| `DATABASE_HOST` | Yes | `db` | Database host hostname (container service name `db` in Docker network). |
| `DATABASE_PORT` | No | `5432` | PostgreSQL listening port. |
| `CONN_MAX_AGE` | No | `60` | Persistent database connection lifetime in seconds. |
| `DATABASE_URL` | No | *Derived* | Optional alternative standard database connection URI. |

### 2.4 Redis & Celery

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Connection string for Redis cache & Django Channels layers. |
| `CELERY_BROKER_URL` | Yes | `redis://redis:6379/0` | Celery task queue message broker URI. |
| `CELERY_RESULT_BACKEND`| Yes | `redis://redis:6379/1` | Celery task result backend URI (database `1`). |

### 2.5 Razorpay Payment Gateway

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `RAZORPAY_KEY_ID` | Yes | `rzp_test_placeholder_key_id` | Razorpay API Key ID. Must start with `rzp_test_`. |
| `RAZORPAY_KEY_SECRET` | Yes | `placeholder_secret_key_staging` | Razorpay API secret key for HMAC signature verification. |
| `RAZORPAY_WEBHOOK_SECRET`| Yes | `placeholder_webhook_secret_staging` | Secret used to verify incoming Razorpay webhook payloads. |
| `RAZORPAY_CURRENCY` | No | `INR` | Three-letter currency code (default: INR). |

### 2.6 Email & Notifications

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `EMAIL_BACKEND` | No | `django.core.mail.backends.console.EmailBackend` | Email backend. Defaults to `console` in staging to prevent sending real emails. |
| `EMAIL_HOST` | No | `localhost` | SMTP host (e.g. Mailpit, Mailgun sandbox, or SendGrid). |
| `EMAIL_PORT` | No | `1025` | SMTP port. |
| `EMAIL_HOST_USER` | No | `""` | SMTP username. |
| `EMAIL_HOST_PASSWORD` | No | `""` | SMTP password. |
| `EMAIL_USE_TLS` | No | `False` | Whether to use TLS encryption with SMTP. |
| `DEFAULT_FROM_EMAIL` | No | `EazyDoc Staging <noreply-staging@eazydoc.com>` | Sender address in outgoing system emails. |

### 2.7 Observability & Storage (Optional)

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `SENTRY_DSN` | No | `""` | Sentry error tracking DSN (environment automatically tagged as `staging`). |
| `SENTRY_TRACES_SAMPLE_RATE`| No | `0.2` | Performance tracing sample rate (0.0 to 1.0). |
| `AWS_STORAGE_BUCKET_NAME`| No | `""` | S3 bucket name if using cloud object storage instead of persistent volume. |
| `AWS_ACCESS_KEY_ID` | No | `""` | AWS IAM access key ID with S3 read/write permissions. |
| `AWS_SECRET_ACCESS_KEY`| No | `""` | AWS IAM secret access key. |
| `AWS_S3_REGION_NAME` | No | `ap-south-1` | AWS S3 region (default: Mumbai). |

---

## 3. Frontend Environment Variables (`frontend/.env.staging`)

| Variable Name | Required | Default in Staging | Description & Constraints |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `/api/v1` | Base URL for backend API calls. Relative `/api/v1` is recommended behind Nginx. |
| `VITE_APP_ENV` | No | `staging` | Environment indicator displayed in staging UI banners or telemetry. |

