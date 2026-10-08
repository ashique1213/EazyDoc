from rest_framework.permissions import BasePermission
from .models import UserRole, UserStatus


class IsAuthenticatedUser(BasePermission):
    """Allows access only to authenticated, active, non-suspended users."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
        )


class IsSuperAdmin(BasePermission):
    """Allows platform-wide access only to SUPER_ADMIN users."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.SUPER_ADMIN
        )


class IsClinicOwner(BasePermission):
    """Allows access only to CLINIC_OWNER users."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.CLINIC_OWNER
        )


class IsStaff(BasePermission):
    """Allows access only to clinic STAFF members."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.STAFF
        )


class IsDoctor(BasePermission):
    """Allows access only to DOCTOR users."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.DOCTOR
        )


class IsPatient(BasePermission):
    """Allows access only to PATIENT users."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role == UserRole.PATIENT
        )


class IsClinicStaffOrOwner(BasePermission):
    """Allows access to clinic administrative roles (Owner or Staff)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.status == UserStatus.ACTIVE
            and user.role in (UserRole.CLINIC_OWNER, UserRole.STAFF)
        )


# ==============================================================================
# Object-Level Authorization Foundations (Multi-Tenant Preparation)
# ==============================================================================
# Execution Hierarchy:
# Authentication -> Role Permission -> Object Permission -> Tenant/Clinic Scoping
# ==============================================================================

class IsObjectOwner(BasePermission):
    """
    Object-level permission allowing users to access only records they own directly.
    Checks `obj.user`, `obj.patient.user`, or `obj` itself if obj is a User.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.role == UserRole.SUPER_ADMIN:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user
        elif hasattr(obj, "patient") and hasattr(obj.patient, "user"):
            return obj.patient.user == request.user
        elif hasattr(obj, "doctor") and hasattr(obj.doctor, "user"):
            return obj.doctor.user == request.user

        return obj == request.user


class IsClinicTenantObject(BasePermission):
    """
    Object-level tenant isolation permission.
    Verifies that the object belongs to the clinic owned or staffed by the requesting user.
    Prevents cross-clinic BOLA / IDOR attacks (e.g. Clinic A mutating Clinic B resources).
    """

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # Super admin has platform-wide authority
        if user.role == UserRole.SUPER_ADMIN:
            return True

        clinic = getattr(obj, "clinic", None)
        if clinic is None and hasattr(obj, "doctor_clinic"):
            clinic = getattr(obj.doctor_clinic, "clinic", None)

        if not clinic:
            return False

        # Clinic Owner check: user must be the verified owner of this clinic
        if user.role == UserRole.CLINIC_OWNER:
            return getattr(clinic, "owner_id", None) == user.id or getattr(clinic, "owner", None) == user

        # Staff check: user must have an active staff association with this clinic
        if user.role == UserRole.STAFF:
            if hasattr(user, "staff_profile"):
                return user.staff_profile.clinic_id == clinic.id

        return False


class TenantObjectPermissionMixin:
    """
    Viewset mixin providing standard tenant query scoping and object permission enforcement.
    Future apps (Clinics, Appointments, Schedules) will inherit from this mixin.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        if user.role == UserRole.SUPER_ADMIN:
            return qs

        if user.role == UserRole.CLINIC_OWNER and hasattr(qs.model, "clinic"):
            return qs.filter(clinic__owner=user)

        if user.role == UserRole.STAFF and hasattr(qs.model, "clinic") and hasattr(user, "staff_profile"):
            return qs.filter(clinic=user.staff_profile.clinic)

        if user.role == UserRole.DOCTOR and hasattr(qs.model, "doctor"):
            return qs.filter(doctor__user=user)

        if user.role == UserRole.PATIENT and hasattr(qs.model, "patient"):
            return qs.filter(patient__user=user)

        return qs
