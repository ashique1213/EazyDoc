import re
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse
from config.logging import set_current_request_id, clear_current_request_id

# Regex to validate incoming X-Request-ID or X-Correlation-ID headers:
# Must be alphanumeric, dashes, or underscores, between 8 and 64 characters long.
# Prevents arbitrary, oversized, or malicious content (e.g. CRLF injection, control characters).
VALID_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")


class RequestIDMiddleware:
    """
    Middleware that establishes and propagates end-to-end Request & Correlation IDs.

    1. Checks incoming HTTP_X_REQUEST_ID and HTTP_X_CORRELATION_ID headers.
    2. Validates against a strict alphanumeric pattern to prevent log injection.
    3. Generates a cryptographically secure UUID4 if absent or invalid.
    4. Binds the ID to contextvars for structured JSON logging across all layers.
    5. Returns the X-Request-ID response header for client-side correlation.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming_id = (
            request.META.get("HTTP_X_REQUEST_ID")
            or request.META.get("HTTP_X_CORRELATION_ID")
            or ""
        ).strip()

        if incoming_id and VALID_REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = f"req_{uuid.uuid4().hex}"

        request.request_id = request_id
        set_current_request_id(request_id)

        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            clear_current_request_id()

