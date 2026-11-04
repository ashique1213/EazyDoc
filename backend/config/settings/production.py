from .base import *

DEBUG = False

# Strict production security
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production Cookie configurations
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
JWT_AUTH_COOKIE_SECURE = env.bool("JWT_AUTH_COOKIE_SECURE", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Logging format defaults to JSON in production
LOG_FORMAT = env("LOG_FORMAT", default="json")
LOGGING["handlers"]["console"]["formatter"] = LOG_FORMAT

# Sentry Error Monitoring (optional via SENTRY_DSN)
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    def before_send_production(event, hint):
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
        environment="production",
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
        before_send=before_send_production,
    )


# AWS S3 Storage configuration (optional via env)
if env("AWS_STORAGE_BUCKET_NAME", default=""):
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-south-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_DEFAULT_ACL = "private"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
    }
