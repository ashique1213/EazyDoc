import json
import logging
import re
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from django.conf import settings

# Thread-safe / Coroutine-safe Context Variable for Request & Correlation ID
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_current_request_id() -> Optional[str]:
    """Retrieve the current execution context's request/correlation ID."""
    return _request_id_ctx.get()


def set_current_request_id(request_id: str) -> None:
    """Set the current execution context's request/correlation ID."""
    _request_id_ctx.set(request_id)


def clear_current_request_id() -> None:
    """Reset the current execution context's request/correlation ID."""
    _request_id_ctx.set(None)


# Sensitive fields that must always be masked in log messages and dictionary payloads
SENSITIVE_FIELD_NAMES = {
    "password",
    "password_confirm",
    "old_password",
    "new_password",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "authorization",
    "secret",
    "key_secret",
    "api_secret",
    "razorpay_key_secret",
    "razorpay_webhook_secret",
    "razorpay_signature",
    "webhook_secret",
    "card",
    "card_number",
    "credit_card",
    "pan",
    "cvv",
    "cvc",
    "security_code",
    "medical_history",
    "diagnosis",
    "clinical_notes",
}

# Regex to redact key-value strings like password=xyz, "token": "abc", Bearer eyJ...
SENSITIVE_STRING_REGEX = re.compile(
    r'(?i)(["\']?(?:'
    + "|".join(re.escape(k) for k in SENSITIVE_FIELD_NAMES)
    + r')["\']?\s*[:=]\s*)(["\']?[^\s"\'\,;]+["\']?)',
)
BEARER_TOKEN_REGEX = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9\-_\.=]+", re.IGNORECASE)


def redact_sensitive_data(obj: Any) -> Any:
    """Recursively scrub sensitive keys and string patterns from structures."""
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            key_lower = str(k).lower()
            if any(sensitive_key in key_lower for sensitive_key in SENSITIVE_FIELD_NAMES):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_sensitive_data(v)
        return sanitized
    elif isinstance(obj, (list, tuple)):
        return [redact_sensitive_data(item) for item in obj]
    elif isinstance(obj, str):
        # Scrub Bearer tokens and sensitive key=value patterns
        scrubbed = BEARER_TOKEN_REGEX.sub(r"\1[REDACTED]", obj)
        scrubbed = SENSITIVE_STRING_REGEX.sub(r"\1[REDACTED]", scrubbed)
        return scrubbed
    return obj


class RequestIDFilter(logging.Filter):
    """Logging filter attaching the active request/correlation ID to LogRecord instances."""

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = getattr(record, "request_id", None) or get_current_request_id()
        record.request_id = req_id if req_id else "-"
        return True


class SensitiveDataFilter(logging.Filter):
    """Logging filter sanitizing credentials, tokens, and PHI before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_data(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_sensitive_data(a) for a in record.args)
        return True


class StructuredJSONFormatter(logging.Formatter):
    """
    High-performance structured JSON formatter compatible with Logstash, CloudWatch,
    Datadog, Grafana Loki, and local Docker logging.
    """

    def __init__(self, *args, app_name="eazydoc", environment=None, **kwargs):
        self.app_name = kwargs.pop("app_name", app_name)
        env = kwargs.pop("environment", environment)
        self.environment = env or getattr(settings, "SENTRY_ENVIRONMENT", None) or (
            "production" if not getattr(settings, "DEBUG", True) else "development"
        )
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        # Standard timestamp in ISO 8601 UTC
        now_utc = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        req_id = getattr(record, "request_id", "-")
        if req_id == "-" or not req_id:
            req_id = get_current_request_id() or "-"

        # Format message safely
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        message = redact_sensitive_data(message)

        log_payload: Dict[str, Any] = {
            "timestamp": now_utc,
            "level": record.levelname,
            "app": self.app_name,
            "environment": self.environment,
            "request_id": req_id,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": message,
        }

        # Include custom extra metadata passed via logger.info("...", extra={...})
        standard_attrs = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "request_id",
        }
        raw_extra = {}
        for key, value in record.__dict__.items():
            if key == "extra" and isinstance(value, dict):
                raw_extra.update(value)
            elif key not in standard_attrs and not key.startswith("_"):
                raw_extra[key] = value

        if raw_extra:
            log_payload["extra"] = redact_sensitive_data(raw_extra)

        # Capture exception details if present
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            log_payload["exception"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": redact_sensitive_data(str(exc_val)),
                "stacktrace": redact_sensitive_data(traceback.format_exception(exc_type, exc_val, exc_tb)),
            }

        return json.dumps(log_payload, default=str)
