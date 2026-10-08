import sys
from .base import *

DEBUG = True

# When running unit tests or when USE_SQLITE is explicitly enabled, use SQLite
if "test" in sys.argv or "pytest" in sys.modules or env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Faster password hashing for development and test execution
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Development channel layer fallback if Redis host is not reachable or in test mode
FALLBACK_IN_MEMORY_CHANNELS = env.bool("FALLBACK_IN_MEMORY_CHANNELS", default=True)
if "test" in sys.argv or FALLBACK_IN_MEMORY_CHANNELS:
    try:
        import redis
        r = redis.from_url(REDIS_URL, socket_connect_timeout=0.5)
        r.ping()
    except Exception:
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
            },
        }

# Internal IPs for debug toolbar if enabled
INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Email backend: console by default in dev
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
