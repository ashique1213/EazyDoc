from rest_framework import status
from rest_framework.exceptions import APIException


class SlotUnavailableException(APIException):
    """Raised when the requested slot is already booked, blocked, or in the past (HTTP 409)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested appointment time slot is no longer available. Please select another slot."
    default_code = "slot_unavailable"

    def __init__(self, detail=None, code=None, conflicting_slot=None):
        super().__init__(detail=detail, code=code)
        if conflicting_slot:
            if isinstance(self.detail, dict):
                self.detail["conflicting_slot"] = conflicting_slot
            else:
                self.detail = {
                    "message": str(detail or self.default_detail),
                    "conflicting_slot": conflicting_slot,
                }


class IdempotencyConflictException(APIException):
    """Raised when an idempotency key is reused with different request payload (HTTP 400)."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This idempotency key was previously submitted with different booking parameters."
    default_code = "idempotency_key_reused_with_different_payload"


class InvalidBookingException(APIException):
    """Raised when booking prerequisites or eligibility rules are violated (HTTP 400)."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid appointment booking request."
    default_code = "invalid_booking"


class CutoffExceededException(APIException):
    """Raised when a patient attempts to cancel or reschedule after the policy cutoff (HTTP 409)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The policy cutoff for cancelling or rescheduling this appointment has passed (11:59:59 PM on the calendar day before the appointment in the clinic's timezone)."
    default_code = "cutoff_exceeded"


class InvalidAppointmentStateException(APIException):
    """Raised when an operation is invalid for the appointment's current lifecycle status (HTTP 409)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This appointment cannot be cancelled or rescheduled in its current status."
    default_code = "invalid_appointment_state"

