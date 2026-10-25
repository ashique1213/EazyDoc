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


def check_clinic_access(user, clinic, required_permission: str = None) -> bool:
    """
    Unified authorization helper for multi-tenant clinic operations.
    Returns True if user is authorized for the given clinic and optional permission.
    """
    if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
        return False

    if user.role == UserRole.SUPER_ADMIN:
        return True

    if user.role == UserRole.CLINIC_OWNER:
        return clinic.owner_id == user.id or clinic.owner == user

    if user.role == UserRole.STAFF:
        staff_profile = getattr(user, "staff_profile", None)
        if not staff_profile or not staff_profile.is_active:
            return False
        if staff_profile.clinic_id != clinic.id:
            return False
        if required_permission:
            return staff_profile.has_permission(required_permission)
        return True

    return False


class HasClinicStaffOrOwnerPermission(BasePermission):
    """
    Permission class for clinic-scoped operations.
    Views can define `required_permission` (a ClinicStaffPermission string).
    - Super Admin: Granted
    - Clinic Owner: Granted
    - Clinic Staff: Granted only if affiliated with this clinic and holds required_permission
    - Other users: Denied
    """

    message = "You do not have authorization to perform this operation for the clinic."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        return user.role in (UserRole.CLINIC_OWNER, UserRole.STAFF, UserRole.SUPER_ADMIN)

    def has_object_permission(self, request, view, obj) -> bool:
        clinic = getattr(obj, "clinic", obj)
        required_perm = getattr(view, "required_permission", None)
        return check_clinic_access(request.user, clinic, required_perm)


class IsClinicOwnerOnly(BasePermission):
    """
    Restricts action strictly to the clinic's verified owner or platform Super Admin.
    Staff members are rejected (e.g. for staff management, profile approvals, sensitive settings).
    """

    message = "Only the clinic owner or super administrator can perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.status == UserStatus.ACTIVE):
            return False
        return user.role in (UserRole.CLINIC_OWNER, UserRole.SUPER_ADMIN)

    def has_object_permission(self, request, view, obj) -> bool:
        clinic = getattr(obj, "clinic", obj)
        user = request.user
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return clinic.owner_id == user.id or clinic.owner == user

