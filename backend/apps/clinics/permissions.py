from rest_framework.permissions import BasePermission
from apps.accounts.models import UserRole, UserStatus


class CanManageClinics(BasePermission):
    """
    Permission check for clinic owners.
    Only authenticated users with CLINIC_OWNER or SUPER_ADMIN role can access.
    Patients, Doctors, and Clinic Staff are rejected.
    """

    message = "Only authorized Clinic Owners or Super Administrators can access this resource."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        return user.role in (UserRole.CLINIC_OWNER, UserRole.SUPER_ADMIN)


class IsClinicOwner(BasePermission):
    """
    Object-level permission: Allows access only if the requesting user is the clinic's owner
    or has platform-wide SUPER_ADMIN privileges.
    """

    message = "You do not have permission to view or manage this clinic."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return obj.owner_id == user.id or obj.owner == user


class IsSuperAdminOnly(BasePermission):
    """
    Allows access strictly to platform Super Administrators.
    """

    message = "This administrative action requires platform Super Administrator privileges."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.SUPER_ADMIN
        )
