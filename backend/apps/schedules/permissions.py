from rest_framework.permissions import BasePermission
from apps.accounts.models import UserRole, UserStatus


class CanManageClinicSchedules(BasePermission):
    """
    Ensures that only authorized Clinic Owners or Staff of the specific clinic
    can create, modify, or deactivate schedules for that clinic.
    Enforces Rule 1, Rule 5, Rule 6.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role in (UserRole.CLINIC_OWNER, UserRole.STAFF, UserRole.SUPER_ADMIN)
        )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.status == UserStatus.ACTIVE):
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        # Extract clinic from DoctorSchedule, BlockedSlot, or DoctorClinic
        clinic = None
        if hasattr(obj, "doctor_clinic") and obj.doctor_clinic:
            clinic = obj.doctor_clinic.clinic
        elif hasattr(obj, "clinic") and obj.clinic:
            clinic = obj.clinic

        if not clinic:
            return False

        if user.role == UserRole.CLINIC_OWNER:
            return clinic.owner_id == user.id

        if user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
            return user.staff_profile.clinic_id == clinic.id

        return False


class CanViewSchedules(BasePermission):
    """
    Allows viewing schedules:
    - Clinic Owner / Staff for their clinics
    - Doctor for their own schedules across clinics (Rule 2)
    - Super Admin
    - Authenticated users for availability slot lookup
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
        )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.status == UserStatus.ACTIVE):
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        # Doctor viewing their own schedule
        if user.role == UserRole.DOCTOR:
            if hasattr(obj, "doctor_clinic") and obj.doctor_clinic:
                return obj.doctor_clinic.doctor.user_id == user.id
            if hasattr(obj, "doctor"):
                return obj.doctor.user_id == user.id

        # Clinic Owner / Staff viewing their clinic's schedule
        clinic = None
        if hasattr(obj, "doctor_clinic") and obj.doctor_clinic:
            clinic = obj.doctor_clinic.clinic
        elif hasattr(obj, "clinic") and obj.clinic:
            clinic = obj.clinic

        if clinic:
            if user.role == UserRole.CLINIC_OWNER:
                return clinic.owner_id == user.id
            if user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
                return user.staff_profile.clinic_id == clinic.id

        return False


class CanManageDoctorUnavailability(BasePermission):
    """
    Doctors can create/view/delete their own leaves.
    Clinic owners and staff can manage leaves or clinic closure for their own clinic.
    """

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role in (UserRole.DOCTOR, UserRole.CLINIC_OWNER, UserRole.STAFF, UserRole.SUPER_ADMIN)
        )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.status == UserStatus.ACTIVE):
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        if user.role == UserRole.DOCTOR:
            return obj.doctor.user_id == user.id

        if user.role == UserRole.CLINIC_OWNER:
            if obj.clinic:
                return obj.clinic.owner_id == user.id
            # If global doctor leave, clinic owner cannot delete it
            return False

        if user.role == UserRole.STAFF and hasattr(user, "staff_profile"):
            if obj.clinic:
                return user.staff_profile.clinic_id == obj.clinic.id
            return False

        return False
