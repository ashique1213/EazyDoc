from rest_framework.permissions import BasePermission
from apps.accounts.models import UserRole, UserStatus


class CanAccessAppointment(BasePermission):
    """
    Object-level permission allowing access to an appointment strictly if:
    1. Requesting user is the booking Patient.
    2. Requesting user is the Doctor assigned to this appointment.
    3. Requesting user is the Clinic Owner of the clinic where appointment takes place.
    4. Requesting user is an authorized Clinic Staff member of that clinic.
    5. Requesting user is a platform Super Administrator.
    """

    message = "You do not have permission to view or manage this appointment."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        # Patient access: only their own appointment
        if user.role == UserRole.PATIENT:
            return obj.patient_id == user.id

        # Doctor access: only appointments for their own doctor profile
        if user.role == UserRole.DOCTOR:
            return obj.doctor.user_id == user.id

        # Clinic Owner access: only appointments at their owned clinic
        if user.role == UserRole.CLINIC_OWNER:
            return obj.clinic.owner_id == user.id

        # Staff access: if staff belongs to the clinic
        if user.role == UserRole.STAFF:
            # Check clinic ownership or affiliation
            return obj.clinic.owner_id == user.id

        return False
