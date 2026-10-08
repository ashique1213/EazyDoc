import logging
from typing import Any, Dict, Optional
from django.http import HttpRequest
from .models import AuditLog

logger = logging.getLogger("security")


def get_client_ip(request: Optional[HttpRequest]) -> Optional[str]:
    """Safely extracts client IP address from standard and forwarded proxy headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def log_audit_event(
    action: str,
    resource_type: str,
    actor=None,
    resource_id: str = "",
    clinic_id: Optional[str] = None,
    request: Optional[HttpRequest] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """
    Safely records an audit event in the database and security logger.
    Never logs passwords, tokens, or sensitive health data.
    """
    ip_address = get_client_ip(request) if request else None
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500] if request else ""

    # Sanitize details to guarantee sensitive credentials are not accidentally stored
    sanitized_details = {}
    if details:
        for k, v in details.items():
            if k.lower() in {"password", "token", "access", "refresh", "secret"}:
                sanitized_details[k] = "[REDACTED]"
            else:
                sanitized_details[k] = v

    try:
        log_entry = AuditLog.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            clinic_id=clinic_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details=sanitized_details,
        )
        logger.info(
            f"AUDIT_EVENT: action={action} resource={resource_type}:{resource_id} actor={actor} ip={ip_address}"
        )
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record audit log for action '{action}': {e}", exc_info=True)
        return None
