import logging
from datetime import timedelta
from typing import Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.subscriptions.models import (
    BillingInterval,
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)

logger = logging.getLogger("apps.subscriptions")


class SubscriptionLifecycleService:
    """
    Orchestrates the lifecycle, state transitions, and trial management of clinic SaaS subscriptions.
    Guarantees deterministic, audited transitions and non-destructive plan modifications.
    """

    ALLOWED_TRANSITIONS = {
        SubscriptionStatus.TRIALING: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.SUSPENDED,
        },
        SubscriptionStatus.ACTIVE: {
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.SUSPENDED,
            SubscriptionStatus.ACTIVE,  # Plan change or renewal
        },
        SubscriptionStatus.PAST_DUE: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.SUSPENDED,
        },
        SubscriptionStatus.CANCELLED: {
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.ACTIVE,  # Reactivation
            SubscriptionStatus.SUSPENDED,
        },
        SubscriptionStatus.EXPIRED: {
            SubscriptionStatus.ACTIVE,  # Re-subscription
            SubscriptionStatus.TRIALING,  # Admin comp/override only
            SubscriptionStatus.SUSPENDED,
        },
        SubscriptionStatus.SUSPENDED: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.TRIALING,
        },
        SubscriptionStatus.INCOMPLETE: {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.EXPIRED,
        },
    }

    @classmethod
    def can_transition(cls, current_status: str, target_status: str) -> bool:
        """Validates if transition from current_status to target_status is allowed."""
        if current_status == target_status:
            return True
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @classmethod
    @transaction.atomic
    def initialize_clinic_subscription(
        cls,
        clinic,
        plan: Optional[SubscriptionPlan] = None,
        trial_days: int = 14,
        triggered_by=None,
    ) -> ClinicSubscription:
        """
        Initializes a new clinic subscription. If the clinic has never had a trial,
        it starts a free trial on Starter/Professional. If trial was previously consumed,
        defaults to the Free Community plan.
        """
        # If clinic already has a subscription, return it
        existing = ClinicSubscription.objects.filter(clinic=clinic).select_related("plan").first()
        if existing:
            return existing

        now = timezone.now()

        # Determine target plan
        if not plan:
            # Check for Starter plan for trial, else Free plan
            plan = (
                SubscriptionPlan.objects.filter(
                    tier=SubscriptionTier.STARTER,
                    billing_interval=BillingInterval.MONTHLY,
                    is_active=True,
                ).first()
                or SubscriptionPlan.objects.filter(
                    tier=SubscriptionTier.FREE,
                    is_active=True,
                ).first()
            )

        if not plan:
            # Fallback creation if seed not run yet
            plan = SubscriptionPlan.objects.create(
                name="Free Community",
                code="free-monthly-fallback",
                tier=SubscriptionTier.FREE,
                billing_interval=BillingInterval.MONTHLY,
                price=0,
                max_doctors=1,
                max_staff=1,
                max_appointments_per_month=50,
            )

        # Start as trial if plan has trial days and plan is not free
        if plan.tier != SubscriptionTier.FREE and trial_days > 0:
            trial_end = now + timedelta(days=trial_days)
            subscription = ClinicSubscription.objects.create(
                clinic=clinic,
                plan=plan,
                status=SubscriptionStatus.TRIALING,
                billing_interval=plan.billing_interval,
                current_period_start=now,
                current_period_end=trial_end,
                trial_start=now,
                trial_end=trial_end,
                has_used_trial=True,
            )
            SubscriptionEvent.objects.create(
                subscription=subscription,
                clinic=clinic,
                event_type=SubscriptionEventType.TRIAL_STARTED,
                old_status="",
                new_status=SubscriptionStatus.TRIALING,
                new_plan_name=plan.name,
                reason=f"Initial {trial_days}-day free trial activated.",
                triggered_by=triggered_by,
                metadata={"trial_days": trial_days, "plan_code": plan.code},
            )
            logger.info("Initialized trial subscription for clinic %s on plan %s", clinic.name, plan.name)
        else:
            # Free tier
            subscription = ClinicSubscription.objects.create(
                clinic=clinic,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                billing_interval=plan.billing_interval,
                current_period_start=now,
                current_period_end=None,  # Free plan does not expire
                has_used_trial=False,
            )
            SubscriptionEvent.objects.create(
                subscription=subscription,
                clinic=clinic,
                event_type=SubscriptionEventType.PLAN_UPGRADED,
                old_status="",
                new_status=SubscriptionStatus.ACTIVE,
                new_plan_name=plan.name,
                reason="Default Free Community plan activated.",
                triggered_by=triggered_by,
            )
            logger.info("Initialized Free subscription for clinic %s", clinic.name)

        return subscription

    @classmethod
    @transaction.atomic
    def activate_subscription(
        cls,
        subscription: ClinicSubscription,
        new_plan: SubscriptionPlan,
        billing_interval: str,
        payment=None,
        triggered_by=None,
        reason: str = "Payment verified successfully",
    ) -> ClinicSubscription:
        """
        Activates or upgrades a subscription to ACTIVE upon successful payment verification.
        Computes new billing period boundaries based on interval.
        """
        old_status = subscription.status
        old_plan = subscription.plan
        now = timezone.now()

        # Compute period duration
        if billing_interval == BillingInterval.YEARLY:
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        subscription.plan = new_plan
        subscription.billing_interval = billing_interval
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = now
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None
        subscription.cancellation_reason = ""
        subscription.past_due_since = None
        subscription.grace_period_ends_at = None
        subscription.save()

        # Determine event type
        if old_status in [SubscriptionStatus.TRIALING, SubscriptionStatus.EXPIRED, SubscriptionStatus.PAST_DUE]:
            event_type = SubscriptionEventType.PAYMENT_SUCCESS
        elif old_plan != new_plan:
            event_type = (
                SubscriptionEventType.PLAN_UPGRADED
                if new_plan.price >= old_plan.price
                else SubscriptionEventType.PLAN_DOWNGRADED
            )
        else:
            event_type = SubscriptionEventType.RENEWED

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=event_type,
            old_status=old_status,
            new_status=SubscriptionStatus.ACTIVE,
            old_plan_name=old_plan.name if old_plan else "",
            new_plan_name=new_plan.name,
            reason=reason,
            triggered_by=triggered_by,
            metadata={
                "billing_interval": billing_interval,
                "current_period_end": period_end.isoformat(),
                "payment_id": str(payment.id) if payment else None,
            },
        )

        logger.info(
            "Activated subscription for clinic %s on plan %s until %s",
            subscription.clinic.name,
            new_plan.name,
            period_end,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def mark_past_due(
        cls,
        subscription: ClinicSubscription,
        reason: str = "Automatic renewal payment charge failed",
        grace_period_days: int = 5,
        triggered_by=None,
    ) -> ClinicSubscription:
        """
        Marks subscription as PAST_DUE when a scheduled payment fails.
        Establishes a grace period during which operational access is maintained.
        """
        if subscription.status != SubscriptionStatus.ACTIVE:
            logger.warning(
                "Cannot mark non-active subscription %s as PAST_DUE (current status: %s)",
                subscription.id,
                subscription.status,
            )
            return subscription

        now = timezone.now()
        old_status = subscription.status
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.past_due_since = now
        subscription.grace_period_ends_at = now + timedelta(days=grace_period_days)
        subscription.save()

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=SubscriptionEventType.PAST_DUE_ENTERED,
            old_status=old_status,
            new_status=SubscriptionStatus.PAST_DUE,
            reason=reason,
            triggered_by=triggered_by,
            metadata={
                "grace_period_days": grace_period_days,
                "grace_period_ends_at": subscription.grace_period_ends_at.isoformat(),
            },
        )
        logger.warning(
            "Subscription %s for clinic %s marked PAST_DUE. Grace period expires %s",
            subscription.id,
            subscription.clinic.name,
            subscription.grace_period_ends_at,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def request_cancellation(
        cls,
        subscription: ClinicSubscription,
        reason: str = "",
        triggered_by=None,
    ) -> ClinicSubscription:
        """
        Records cancellation request. Keeps subscription active until current period ends.
        Does NOT immediately revoke access or delete any resources.
        """
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE]:
            raise ValidationError(_("Only active, trialing, or past due subscriptions can be cancelled."))

        old_status = subscription.status
        now = timezone.now()

        subscription.cancel_at_period_end = True
        subscription.cancelled_at = now
        subscription.cancellation_reason = reason
        # If already trialing and cancelled, or no end date, we mark CANCELLED immediately
        if subscription.status == SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.CANCELLED

        subscription.save()

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=SubscriptionEventType.CANCELLATION_REQUESTED,
            old_status=old_status,
            new_status=subscription.status,
            reason=reason or "Cancellation requested by clinic owner.",
            triggered_by=triggered_by,
            metadata={
                "cancel_at_period_end": True,
                "period_ends_at": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            },
        )
        logger.info(
            "Cancellation recorded for clinic %s subscription. Active until %s",
            subscription.clinic.name,
            subscription.current_period_end,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def expire_subscription(
        cls,
        subscription: ClinicSubscription,
        reason: str = "Subscription period or free trial has expired",
        fallback_to_free: bool = True,
        triggered_by=None,
    ) -> ClinicSubscription:
        """
        Handles expiration of trials, cancelled subscriptions, or elapsed grace periods.
        Safely reverts to the Free Community plan if fallback_to_free is True.
        ZERO clinic data (doctors, staff, appointments) is destroyed.
        """
        old_status = subscription.status
        old_plan = subscription.plan

        free_plan = SubscriptionPlan.objects.filter(
            tier=SubscriptionTier.FREE,
            is_active=True,
        ).first()

        if fallback_to_free and free_plan:
            subscription.plan = free_plan
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.billing_interval = BillingInterval.MONTHLY
            subscription.current_period_start = timezone.now()
            subscription.current_period_end = None
            subscription.cancel_at_period_end = False
            subscription.past_due_since = None
            subscription.grace_period_ends_at = None
            subscription.save()

            event_type = SubscriptionEventType.PLAN_DOWNGRADED
            new_status = SubscriptionStatus.ACTIVE
            new_plan_name = free_plan.name
            event_reason = f"{reason}. Reverted to Free Community plan."
        else:
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.save()
            event_type = SubscriptionEventType.EXPIRED
            new_status = SubscriptionStatus.EXPIRED
            new_plan_name = old_plan.name
            event_reason = reason

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            old_plan_name=old_plan.name,
            new_plan_name=new_plan_name,
            reason=event_reason,
            triggered_by=triggered_by,
        )
        logger.info(
            "Subscription %s for clinic %s transitioned to %s",
            subscription.id,
            subscription.clinic.name,
            new_status,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def suspend_subscription(
        cls,
        subscription: ClinicSubscription,
        reason: str,
        admin_user=None,
    ) -> ClinicSubscription:
        """Administrative lock restricting platform operations."""
        old_status = subscription.status
        subscription.status = SubscriptionStatus.SUSPENDED
        subscription.save()

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=SubscriptionEventType.SUSPENDED,
            old_status=old_status,
            new_status=SubscriptionStatus.SUSPENDED,
            reason=reason,
            triggered_by=admin_user,
        )
        logger.warning(
            "Subscription %s suspended by admin %s. Reason: %s",
            subscription.id,
            admin_user,
            reason,
        )
        return subscription

    @classmethod
    @transaction.atomic
    def reinstate_subscription(
        cls,
        subscription: ClinicSubscription,
        admin_user=None,
        reason: str = "Reinstated by Super Admin",
    ) -> ClinicSubscription:
        """Administrative reinstatement of a suspended subscription."""
        old_status = subscription.status
        now = timezone.now()

        # Check if period is still valid
        if subscription.current_period_end and subscription.current_period_end > now:
            subscription.status = SubscriptionStatus.ACTIVE
        elif subscription.trial_end and subscription.trial_end > now:
            subscription.status = SubscriptionStatus.TRIALING
        else:
            subscription.status = SubscriptionStatus.ACTIVE
            # Extend 30 days if expired
            subscription.current_period_start = now
            subscription.current_period_end = now + timedelta(days=30)

        subscription.save()

        SubscriptionEvent.objects.create(
            subscription=subscription,
            clinic=subscription.clinic,
            event_type=SubscriptionEventType.REINSTATED,
            old_status=old_status,
            new_status=subscription.status,
            reason=reason,
            triggered_by=admin_user,
        )
        logger.info("Subscription %s reinstated by admin %s", subscription.id, admin_user)
        return subscription
