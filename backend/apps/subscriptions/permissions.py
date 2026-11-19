import logging
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from apps.clinics.models import Clinic
from apps.subscriptions.services.entitlements import EntitlementService

logger = logging.getLogger("apps.subscriptions")


class IsClinicOwnerOrSuperAdmin(permissions.BasePermission):
    """
    Grants access if the user is a SUPER_ADMIN or the authenticated CLINIC_OWNER of the targeted clinic.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "SUPER_ADMIN":
            return True

        # Extract clinic_id from URL kwargs
        clinic_id = view.kwargs.get("clinic_id") or view.kwargs.get("pk")
        if not clinic_id:
            return True

        return Clinic.objects.filter(id=clinic_id, owner=request.user).exists()


class HasSubscriptionFeature(permissions.BasePermission):
    """
    Reusable DRF permission checking whether the clinic holds an active subscription
    with a specific feature flag (e.g. 'advanced_analytics', 'export_reports').
    """
    required_feature = ""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "SUPER_ADMIN":
            return True

        clinic_id = view.kwargs.get("clinic_id")
        if not clinic_id:
            return True

        clinic = Clinic.objects.filter(id=clinic_id).first()
        if not clinic:
            return False

        feature = getattr(view, "required_subscription_feature", self.required_feature)
        if not feature:
            return True

        if not EntitlementService.has_feature(clinic, feature):
            raise PermissionDenied(
                f"Your subscription plan does not include the '{feature}' capability. "
                "Please upgrade your plan to unlock this feature."
            )
        return True
