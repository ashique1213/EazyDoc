import logging
from decimal import Decimal
from .base import *

# Staging Environment Mode: DEBUG must strictly remain False
DEBUG = False

logger = logging.getLogger("config.settings.staging")
logger.info("Initializing EazyDoc Staging Settings...")

# Secret key must be provided via environment in staging
SECRET_KEY = env("SECRET_KEY", default="django-insecure-eazydoc-staging-secret-key-change-in-env-before-deploy")

# Host and Network Configuration
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "backend",
        "nginx",
        "staging.eazydoc.internal",
        "staging.eazydoc.com",
    ],
)

# CORS and CSRF Configuration for Staging
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1",
        "http://localhost:80",
        "http://localhost:5173",
        "https://staging.eazydoc.internal",
        "https://staging.eazydoc.com",
    ],
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
        "https://127.0.0.1",
        "http://localhost:80",
        "http://localhost:5173",
        "https://staging.eazydoc.internal",
        "https://staging.eazydoc.com",
    ],
)

# Reverse Proxy & SSL Configuration
# When behind Nginx or an Application Load Balancer terminating TLS:
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)

# Cookie Security (Can be toggled via env based on staging TLS certificate availability)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
JWT_AUTH_COOKIE_SECURE = env.bool("JWT_AUTH_COOKIE_SECURE", default=False)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Browser Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HSTS Settings (Default to 0 in staging to avoid locking browser caches during testing)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = False

# Database Connection Settings
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# Staging Email Safety Configuration
# Defaults to console backend or safe staging SMTP to prevent unintended real messages
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="EazyDoc Staging <noreply-staging@eazydoc.com>")

# Razorpay Staging Guard
# Staging MUST use test keys only; live credentials will raise a hard exception
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="rzp_test_placeholder_key_id")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="placeholder_secret_key_staging")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="placeholder_webhook_secret_staging")

if RAZORPAY_KEY_ID.startswith("rzp_live_"):
    raise ValueError(
        "CRITICAL SECURITY HAZARD: Razorpay LIVE key detected in staging settings! "
        "Staging environments must exclusively use Razorpay test keys (rzp_test_*)."
    )

# Logging format defaults to JSON in staging
LOG_FORMAT = env("LOG_FORMAT", default="json")
LOGGING["handlers"]["console"]["formatter"] = LOG_FORMAT

# Sentry Monitoring Configuration for Staging
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    def before_send_staging(event, hint):
        """Scrub authentication headers, cookies, and patient-sensitive payloads before transmission."""
        if "request" in event:
            headers = event["request"].get("headers", {})
            for h in ("authorization", "cookie", "x-csrftoken"):
                if h in headers:
                    headers[h] = "[REDACTED]"
            if "data" in event["request"] and isinstance(event["request"]["data"], dict):
                from config.logging import redact_sensitive_data
                event["request"]["data"] = redact_sensitive_data(event["request"]["data"])
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment="staging",
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.2),
        send_default_pii=False,
        before_send=before_send_staging,
    )

