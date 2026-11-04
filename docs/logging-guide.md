# EazyDoc — Application Logging & Telemetry Guide

This guide establishes the logging standards, structured schema, sensitive data redaction policies, and query techniques for developers and DevOps engineers on the EazyDoc platform.

---

## 1. Core Principles

1. **Structured by Default**: In staging and production environments, all logs are output in standard Single-Line JSON (NDJSON) format to `stdout`/`stderr`.
2. **Every Transaction Has a Correlation ID**: Every HTTP request and Celery background task is stamped with an `X-Request-ID` (`req_<uuid4>`).
3. **Zero Sensitive Data in Logs**: Passwords, API tokens, credit card CVV/PAN, Razorpay webhooks signatures, and Protected Health Information (PHI) are scrubbed before emission.
4. **Actionable Context**: Logs must provide operational context (e.g. `booking_reference`, `clinic_id`, `doctor_id`, `duration_ms`), not just generic text strings.

---

## 2. Structured Log Schema

Every structured log entry contains the following root keys:

| Field Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `timestamp` | string | ISO 8601 UTC timestamp with microsecond resolution | `"2026-11-04T08:15:20.120456Z"` |
| `level` | string | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `"INFO"` |
| `app` | string | Application identifier | `"eazydoc"` |
| `environment` | string | Deployment environment (`staging`, `production`, `development`) | `"staging"` |
| `request_id` | string | Trace correlation ID (`req_<uuid>` or sanitized client header) | `"req_45ce1d3a4755487eb149232c0a0307e9"` |
| `logger` | string | Name of the emitting logger | `"apps.appointments"` |
| `module` | string | Python file / module name | `"services"` |
| `line` | integer | Line number in source code | `333` |
| `message` | string | Human-readable log message (sanitized) | `"Appointment successfully booked: EZD-202611-8D9V78"` |
| `extra` | object | Optional dictionary of structured domain attributes | `{"booking_reference": "EZD-202611-8D9V78"}` |
| `exception` | object | Present only on errors (`type`, `message`, `stacktrace`) | `{"type": "IntegrityError", ...}` |

---

## 3. Log Levels & Usage Guidelines

### `DEBUG`
- **Purpose**: Fine-grained diagnostic information for local development.
- **When to use**: Inspecting ORM query execution parameters, cache hit/miss details, internal intermediate data structures.
- **Production policy**: Suppressed in staging/production (`LOG_LEVEL=INFO`).

### `INFO`
- **Purpose**: Key lifecycle events confirming expected application behavior.
- **When to use**: User logins, appointment creations, cancellations, status transitions, doctor verifications, webhook processing success, Celery task completions.
- **Production policy**: Always captured.

### `WARNING`
- **Purpose**: Unexpected situations that did not crash the request but require attention.
- **When to use**: Failed authentication attempts (rate limits, bad credentials), duplicate webhook deliveries, Redis cache fallbacks, slow query warnings (> 500ms).
- **Production policy**: Always captured; evaluated for metric alerts.

### `ERROR`
- **Purpose**: Critical operation failures affecting an individual transaction or user.
- **When to use**: Webhook signature verification failure, payment processing rejection, email/SMS provider delivery failure, unhandled 500 exceptions, DB timeout errors.
- **Production policy**: Always captured and routed to Sentry with scrubbed payload.

### `CRITICAL`
- **Purpose**: Complete system degradation, infrastructure partition, or severe data integrity failure.
- **When to use**: Database unreachable, primary Redis crash, data corruption detected, unauthorized privilege escalation attempt.
- **Production policy**: Triggers immediate P1 on-call paging (PagerDuty / Opsgenie).

---

## 4. Sensitive Data Redaction Rules

The `SensitiveDataFilter` and `redact_sensitive_data` engine inspect both string messages and structured `extra={...}` dictionaries.

### Redaction Rules:
1. **Key Name Matching**: Any key containing (case-insensitive) the following substrings is replaced with `"[REDACTED]"`:
   - `password`, `token`, `secret`, `jwt`, `authorization`
   - `razorpay_key_secret`, `razorpay_signature`, `webhook_secret`
   - `card`, `cvv`, `cvc`, `pan`, `security_code`
   - `medical_history`, `diagnosis`, `clinical_notes`
2. **Bearer Token Scrubbing**: Any string matching `Bearer [A-Za-z0-9\-_\.=]+` is transformed to `Bearer [REDACTED]`.
3. **Key-Value String Matching**: Patterns matching `password=xyz`, `"token": "abc"` in plain text strings are masked automatically.

---

## 5. Developer Logging Standards & Code Examples

### 5.1 Emitting Structured Logs in Views or Services
```python
import logging

logger = logging.getLogger(__name__)

# Correct Pattern: Pass structured metadata in `extra`
logger.info(
    f"Appointment booked: {appointment.booking_reference}",
    extra={
        "booking_reference": appointment.booking_reference,
        "clinic_id": str(clinic.id),
        "doctor_id": str(doctor.id),
        "amount": str(appointment.consultation_fee),
    }
)
```

### 5.2 Logging Errors with Exceptions
```python
try:
    payment_service.capture_payment(payment_id)
except PaymentGatewayError as exc:
    # `exc_info=True` automatically attaches stack trace to log
    logger.error(
        f"Failed to capture payment for reference {booking_ref}: {exc}",
        exc_info=True,
        extra={"booking_reference": booking_ref, "gateway": "razorpay"}
    )
```

### 5.3 Logging in Celery Tasks
```python
@shared_task(bind=True, max_retries=3)
def process_webhook_task(self, event_id: str):
    logger.info(
        f"Processing payment webhook: {event_id}",
        extra={"webhook_event_id": event_id}
    )
```

---

## 6. Sample Log Outputs

### INFO Level (Appointment Booked)
```json
{
  "timestamp": "2026-11-04T08:15:20.120456Z",
  "level": "INFO",
  "app": "eazydoc",
  "environment": "staging",
  "request_id": "req_88f912c4ba914c62b512c3f87a912e91",
  "logger": "apps.appointments.services",
  "module": "services",
  "line": 333,
  "message": "Appointment successfully booked: EZD-202611-8D9V78",
  "extra": {
    "booking_reference": "EZD-202611-8D9V78",
    "clinic_id": "8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
    "doctor_id": "7b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"
  }
}
```

### WARNING Level (Failed Login Attempt)
```json
{
  "timestamp": "2026-11-04T08:18:44.890123Z",
  "level": "WARNING",
  "app": "eazydoc",
  "environment": "staging",
  "request_id": "req_e1234abcd5678ef0123456789abcdef0",
  "logger": "apps.accounts.views",
  "module": "views",
  "line": 154,
  "message": "Failed login attempt for user 'doctor@clinic.com': Invalid credentials",
  "extra": {
    "email": "doctor@clinic.com",
    "ip_address": "203.0.113.45"
  }
}
```

### ERROR Level (Payment Webhook Signature Failed)
```json
{
  "timestamp": "2026-11-04T08:22:11.450678Z",
  "level": "ERROR",
  "app": "eazydoc",
  "environment": "staging",
  "request_id": "req_f9876543210fedcba9876543210fedcb",
  "logger": "apps.payments.views",
  "module": "views",
  "line": 88,
  "message": "Payment webhook signature verification failed",
  "extra": {
    "event_id": "evt_rzp_9998881",
    "signature": "[REDACTED]"
  },
  "exception": {
    "type": "SignatureVerificationError",
    "message": "Invalid webhook HMAC signature for payload digest",
    "stacktrace": [
      "File \"/app/backend/apps/payments/views.py\", line 85, in post\n    verify_webhook_signature(body, signature)\n"
    ]
  }
}
```

---

## 7. Querying Logs in Docker, Loki, and CloudWatch

### 7.1 Docker Compose Log Filtering
```bash
# Follow staging backend logs in real-time
docker compose -f docker-compose.staging.yml logs -f backend

# Search logs for a specific Correlation ID
docker compose -f docker-compose.staging.yml logs backend | grep "req_88f912c4ba914c62b512c3f87a912e91"

# Filter logs for WARNING and ERROR levels only using jq
docker compose -f docker-compose.staging.yml logs --no-log-prefix backend \
  | jq -R 'fromjson? | select(.level == "ERROR" or .level == "WARNING")'
```

### 7.2 Grafana Loki LogQL Queries
```logql
# Find all errors in staging backend
{app="eazydoc", environment="staging"} | json | level="ERROR"

# Filter logs by specific booking reference
{app="eazydoc"} | json | extra_booking_reference="EZD-202611-8D9V78"

# Correlate logs across API and Celery using request ID
{app="eazydoc"} | json | request_id="req_45ce1d3a4755487eb149232c0a0307e9"
```

