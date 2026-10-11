from rest_framework.permissions import BasePermission
from apps.accounts.models import UserRole, UserStatus


class IsDoctorUser(BasePermission):
    """
    Allows access only to authenticated users who hold the DOCTOR role.
    Patients, Clinic Staff, and Clinic Owners are rejected.
    """

    message = "Only registered practitioners with the Doctor role can access this resource."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        return user.role == UserRole.DOCTOR


class IsSuperAdminOnly(BasePermission):
    """
    Restricts access strictly to platform Super Administrators.
    """

    message = "This administrative verification action requires platform Super Administrator privileges."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.SUPER_ADMIN
        )


class CanLookupDoctorRegistration(BasePermission):
    """
    Allows authorized Clinic Owners and Super Admins to perform privacy-preserving
    medical registration number lookups. Patients and unauthenticated users receive 403 / 401.
    """

    message = "Only authorized Clinic Owners or Super Administrators can look up doctor registrations."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        return user.role in (UserRole.CLINIC_OWNER, UserRole.SUPER_ADMIN)


class IsDoctorProfileOwner(BasePermission):
    """
    Object-level permission allowing a doctor to view or edit their own profile,
    or a Super Admin to perform oversight.
    """

    message = "You do not have permission to view or modify this doctor profile."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return obj.user_id == user.id or obj.user == user


class IsDoctorDocumentOwnerOrAdmin(BasePermission):
    """
    Object-level permission allowing a doctor to access their own uploaded verification documents,
    or a Super Admin to inspect them during review.
    """

    message = "You do not have permission to access this verification document."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return obj.doctor.user_id == user.id
