import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from typing import Any, Dict, List
from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.subscriptions.models import (
    BillingInterval,
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)

logger = logging.getLogger("apps.subscriptions")


class SubscriptionAnalyticsService:
    """
    Computes SaaS subscription business intelligence metrics for the Super Admin console:
    MRR, ARR, churn rate, active paid subscriptions, plan distributions, and recent audit activity.
    """

    @classmethod
    def get_subscription_metrics(cls) -> Dict[str, Any]:
        """
        Calculates platform-wide SaaS financial and subscription health metrics.
        """
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Active paid subscriptions (excluding FREE tier)
        active_paid_subs = (
            ClinicSubscription.objects.filter(
                status=SubscriptionStatus.ACTIVE,
            )
            .exclude(plan__tier=SubscriptionTier.FREE)
            .select_related("plan")
        )

        mrr = Decimal("0.00")
        for sub in active_paid_subs:
            if sub.billing_interval == BillingInterval.YEARLY:
                mrr += (sub.plan.price / Decimal("12.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                mrr += sub.plan.price

        arr = (mrr * Decimal("12.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        active_paid_count = active_paid_subs.count()
        trialing_count = ClinicSubscription.objects.filter(status=SubscriptionStatus.TRIALING).count()
        total_clinics_subscribed = ClinicSubscription.objects.count()
        past_due_count = ClinicSubscription.objects.filter(status=SubscriptionStatus.PAST_DUE).count()
        cancelled_count = ClinicSubscription.objects.filter(status=SubscriptionStatus.CANCELLED).count()
        expired_count = ClinicSubscription.objects.filter(status=SubscriptionStatus.EXPIRED).count()

        # Churn rate: cancelled or expired in last 30 days / (active + cancelled in last 30 days)
        recent_churned = ClinicSubscription.objects.filter(
            Q(status=SubscriptionStatus.EXPIRED) | Q(status=SubscriptionStatus.CANCELLED),
            updated_at__gte=thirty_days_ago,
        ).exclude(plan__tier=SubscriptionTier.FREE).count()

        denominator = active_paid_count + recent_churned
        churn_rate = 0.0
        if denominator > 0:
            churn_rate = round((recent_churned / denominator) * 100, 2)

        # Total revenue collected all-time
        total_saas_revenue = SubscriptionPayment.objects.filter(
            status=SubscriptionPaymentStatus.SUCCESS
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Plan distribution
        plan_distribution = []
        plans = SubscriptionPlan.objects.filter(is_active=True).annotate(
            active_clinics_count=Count(
                "clinic_subscriptions",
                filter=Q(clinic_subscriptions__status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            )
        ).order_by("sort_order")

        for plan in plans:
            plan_distribution.append({
                "plan_id": str(plan.id),
                "plan_name": plan.name,
                "tier": plan.tier,
                "billing_interval": plan.billing_interval,
                "price": float(plan.price),
                "active_clinics": plan.active_clinics_count,
            })

        return {
            "mrr": float(mrr),
            "arr": float(arr),
            "total_saas_revenue": float(total_saas_revenue),
            "active_paid_subscriptions": active_paid_count,
            "trialing_subscriptions": trialing_count,
            "past_due_subscriptions": past_due_count,
            "cancelled_subscriptions": cancelled_count,
            "expired_subscriptions": expired_count,
            "total_clinics_enrolled": total_clinics_subscribed,
            "churn_rate_percentage": churn_rate,
            "plan_distribution": plan_distribution,
        }

    @classmethod
    def get_recent_subscription_events(cls, limit: int = 25) -> List[Dict[str, Any]]:
        """Returns recent audit events across all clinic subscriptions."""
        events = (
            SubscriptionEvent.objects.select_related("clinic", "subscription", "triggered_by")
            .order_by("-created_at")[:limit]
        )
        return [
            {
                "id": str(e.id),
                "clinic_id": str(e.clinic.id),
                "clinic_name": e.clinic.name,
                "event_type": e.event_type,
                "old_status": e.old_status,
                "new_status": e.new_status,
                "old_plan_name": e.old_plan_name,
                "new_plan_name": e.new_plan_name,
                "reason": e.reason,
                "triggered_by": e.triggered_by.get_full_name() or e.triggered_by.email if e.triggered_by else "System",
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
