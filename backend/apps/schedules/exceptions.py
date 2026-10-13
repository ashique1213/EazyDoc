from rest_framework import status
from rest_framework.exceptions import APIException


class ScheduleConflictException(APIException):
    """
    Raised when a proposed schedule interval conflicts with an existing shift
    for the same doctor at the same or another clinic, or violates cross-clinic travel buffer.
    Returns HTTP 409 Conflict.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The proposed schedule conflicts with an existing shift or travel buffer."
    default_code = "schedule_conflict"

    def __init__(self, detail=None, conflict_data=None):
        if detail is not None:
            self.detail = {
                "message": detail,
                "conflict": conflict_data or {},
            }
        else:
            self.detail = {
                "message": self.default_detail,
                "conflict": conflict_data or {},
            }


class InactiveAssociationException(APIException):
    """Raised when scheduling is attempted for an inactive doctor-clinic affiliation."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Cannot configure schedules for an inactive or unapproved affiliation."
    default_code = "inactive_association"
