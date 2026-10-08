import logging
from typing import Any, Dict
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Standardized DRF Exception Handler guaranteeing consistent contract:
    {
        "success": false,
        "message": "Human-readable summary",
        "errors": { "field": ["detail"] }
    }
    Never leaks sensitive server traces or unformatted raw dictionaries.
    """
    # Convert standard Django exceptions to DRF counterparts if encountered
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif exc.__class__.__name__ in ("TokenError", "TokenBackendError"):
        exc = exceptions.AuthenticationFailed(detail=str(exc))

    response = exception_handler(exc, context)

    if response is not None:
        errors = {}
        message = "An error occurred."

        if isinstance(response.data, dict):
            # Check for generic detail key
            if "detail" in response.data:
                message = str(response.data["detail"])
                # Remove detail from errors dictionary
                errors = {k: v for k, v in response.data.items() if k != "detail"}
            else:
                message = "Validation failed."
                errors = response.data
        elif isinstance(response.data, list):
            message = "Validation failed."
            errors = {"non_field_errors": response.data}
        else:
            message = str(response.data)

        # Ensure errors dictionary values are lists
        formatted_errors = {}
        for field, err in errors.items():
            if isinstance(err, list):
                formatted_errors[field] = [str(e) for e in err]
            elif isinstance(err, dict):
                formatted_errors[field] = err
            else:
                formatted_errors[field] = [str(err)]

        response.data = {
            "success": False,
            "message": message,
            "errors": formatted_errors,
        }
        return response

    # Unhandled 500 exceptions
    logger.exception(f"Unhandled server exception: {exc}")
    return Response(
        {
            "success": False,
            "message": "An internal server error occurred. Please try again later.",
            "errors": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
