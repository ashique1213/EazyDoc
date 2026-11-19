import logging
from typing import Any, Dict, Optional, Tuple
from django.utils import timezone

from apps.clinics.models import Clinic, DoctorClinic, DoctorClinicStatus, ClinicStaff
from apps.appointments.models import Appointment
from apps.subscriptions.models import ClinicSubscription, SubscriptionStatus
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService

logger = logging.getLogger("apps.subscriptions")


class EntitlementService:
    """
    Centralized SaaS entitlement and quota enforcement service.
    Enforces doctor, staff, and appointment limits based on active subscription tiers.
    Provides non-destructive verification without modifying or deleting existing records.
    """

    @classmethod
    def get_clinic_subscription(cls, clinic: Clinic) -> ClinicSubscription:
        """
        Retrieves the clinic's active subscription, or auto-initializes a standard
        free trial / free tier if none exists yet.
        """
        subscription = (
            ClinicSubscription.objects.filter(clinic=clinic)
            .select_related("plan")
            .first()
        )
        if not subscription:
            subscription = SubscriptionLifecycleService.initialize_clinic_subscription(clinic)
        return subscription

    @classmethod
    def get_active_doctor_count(cls, clinic: Clinic) -> int:
        """
        Counts affiliated doctors who occupy a doctor license seat (ACTIVE and INVITED).
        Removed and rejected associations do not consume license quotas.
        """
        return DoctorClinic.objects.filter(
            clinic=clinic,
            status__in=[DoctorClinicStatus.ACTIVE, DoctorClinicStatus.INVITED],
        ).count()

    @classmethod
    def get_active_staff_count(cls, clinic: Clinic) -> int:
        """Counts active clinic staff members possessing active profiles."""
        return ClinicStaff.objects.filter(clinic=clinic, is_active=True).count()

    @classmethod
    def get_monthly_appointments_count(cls, clinic: Clinic) -> int:
        """Counts appointments booked in the current calendar month."""
        now = timezone.now()
        return Appointment.objects.filter(
            clinic=clinic,
            created_at__year=now.year,
            created_at__month=now.month,
        ).count()

    @classmethod
    def can_add_doctor(cls, clinic: Clinic) -> Tuple[bool, str]:
        """
        Validates if the clinic is permitted to invite or affiliate an additional doctor.
        Returns (is_allowed, error_message).
        """
        sub = cls.get_clinic_subscription(clinic)

        if not sub.is_usable:
            return False, f"Clinic subscription is currently {sub.status}. Please reactivate your subscription."

        limit = sub.effective_max_doctors
        if limit is None:
            return True, ""  # Unlimited doctors

        current_count = cls.get_active_doctor_count(clinic)
        if current_count >= limit:
            return False, (
                f"Doctor seat limit of {limit} reached for your {sub.plan.name} plan "
                f"(current active/invited: {current_count}). Please upgrade your plan to affiliate more doctors."
            )

        return True, ""

    @classmethod
    def can_add_staff(cls, clinic: Clinic) -> Tuple[bool, str]:
        """
        Validates if the clinic is permitted to invite an additional staff account.
        Returns (is_allowed, error_message).
        """
        sub = cls.get_clinic_subscription(clinic)

        if not sub.is_usable:
            return False, f"Clinic subscription is currently {sub.status}. Please reactivate your subscription."

        limit = sub.effective_max_staff
        if limit is None:
            return True, ""  # Unlimited staff

        current_count = cls.get_active_staff_count(clinic)
        if current_count >= limit:
            return False, (
                f"Staff seat limit of {limit} reached for your {sub.plan.name} plan "
                f"(current active: {current_count}). Please upgrade your plan to invite more staff."
            )

        return True, ""

    @classmethod
    def can_book_appointment(cls, clinic: Clinic) -> Tuple[bool, str]:
        """Validates if the clinic has remaining monthly booking quota."""
        sub = cls.get_clinic_subscription(clinic)

        if not sub.is_usable:
            return False, f"Clinic subscription is currently {sub.status}."

        limit = sub.plan.max_appointments_per_month
        if limit is None:
            return True, ""  # Unlimited appointments

        current_count = cls.get_monthly_appointments_count(clinic)
        if current_count >= limit:
            return False, (
                f"Monthly appointment booking quota of {limit} reached for {sub.plan.name} plan. "
                f"Please upgrade to continue receiving new bookings."
            )

        return True, ""

    @classmethod
    def has_feature(cls, clinic: Clinic, feature_flag: str) -> bool:
        """Checks if a boolean feature entitlement flag is active for the clinic."""
        sub = cls.get_clinic_subscription(clinic)
        if not sub.is_usable:
            return False

        flags = sub.plan.feature_flags or {}
        return bool(flags.get(feature_flag, False))

    @classmethod
    def get_clinic_entitlements_summary(cls, clinic: Clinic) -> Dict[str, Any]:
        """
        Compiles a comprehensive entitlement and usage report for frontend display,
        dashboard cards, and permission checks.
        """
        sub = cls.get_clinic_subscription(clinic)
        doc_count = cls.get_active_doctor_count(clinic)
        staff_count = cls.get_active_staff_count(clinic)
        appt_count = cls.get_monthly_appointments_count(clinic)

        max_docs = sub.effective_max_doctors
        max_staff = sub.effective_max_staff
        max_appts = sub.plan.max_appointments_per_month

        can_add_doc, doc_err = cls.can_add_doctor(clinic)
        can_add_stf, stf_err = cls.can_add_staff(clinic)
        can_bk_appt, appt_err = cls.can_book_appointment(clinic)

        def calc_pct(current: int, limit: Optional[int]) -> int:
            if not limit:
                return 0
            return min(100, int((current / limit) * 100))

        days_remaining = 0
        if sub.status == SubscriptionStatus.TRIALING and sub.trial_end:
            days_remaining = max(0, (sub.trial_end - timezone.now()).days)
        elif sub.current_period_end:
            days_remaining = max(0, (sub.current_period_end - timezone.now()).days)

        return {
            "clinic_id": str(clinic.id),
            "clinic_name": clinic.name,
            "subscription": {
                "id": str(sub.id),
                "status": sub.status,
                "tier": sub.plan.tier,
                "plan_name": sub.plan.name,
                "plan_code": sub.plan.code,
                "price": float(sub.plan.price),
                "billing_interval": sub.billing_interval,
                "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "trial_start": sub.trial_start.isoformat() if sub.trial_start else None,
                "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                "is_in_trial": sub.is_in_trial,
                "days_remaining": days_remaining,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "has_used_trial": sub.has_used_trial,
            },
            "doctors": {
                "current": doc_count,
                "limit": max_docs,
                "is_unlimited": max_docs is None,
                "percentage": calc_pct(doc_count, max_docs),
                "can_add": can_add_doc,
                "restriction_message": doc_err,
            },
            "staff": {
                "current": staff_count,
                "limit": max_staff,
                "is_unlimited": max_staff is None,
                "percentage": calc_pct(staff_count, max_staff),
                "can_add": can_add_stf,
                "restriction_message": stf_err,
            },
            "appointments": {
                "current_monthly": appt_count,
                "limit": max_appts,
                "is_unlimited": max_appts is None,
                "percentage": calc_pct(appt_count, max_appts),
                "can_book": can_bk_appt,
                "restriction_message": appt_err,
            },
            "feature_flags": sub.plan.feature_flags or {},
            "marketing_features": sub.plan.features or [],
        }
