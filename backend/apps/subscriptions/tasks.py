import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from apps.notifications.services import NotificationService
from apps.subscriptions.models import (
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionStatus,
    SubscriptionTier,
)
from apps.subscriptions.services.lifecycle import SubscriptionLifecycleService

logger = logging.getLogger("apps.subscriptions")


@shared_task(name="apps.subscriptions.tasks.check_expiring_trials_task")
def check_expiring_trials_task():
    """
    Daily automated scan for free trials:
    1. Sends a 3-day warning alert to clinic owners whose trial will elapse soon.
    2. Gracefully expires elapsed trials and falls back to Free Community tier.
    """
    now = timezone.now()
    three_days_later = now + timedelta(days=3)

    # 1. Trial expiring soon warning (trials ending within next 3 days that haven't received warning)
    expiring_soon_subs = ClinicSubscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__gt=now,
        trial_end__lte=three_days_later,
    ).select_related("clinic", "clinic__owner", "plan")

    warning_count = 0
    for sub in expiring_soon_subs:
        days_left = max(1, (sub.trial_end - now).days)
        # Avoid duplicate warning if already recorded in metadata
        if sub.metadata.get("trial_warning_sent"):
            continue

        try:
            NotificationService.send_notification(
                recipient=sub.clinic.owner,
                notification_type="SUBSCRIPTION_TRIAL_EXPIRING",
                title=f"Free Trial Expiring in {days_left} Days",
                message=(
                    f"Your {sub.plan.name} free trial for {sub.clinic.name} ends on "
                    f"{sub.trial_end.strftime('%d %b %Y')}. Upgrade now to retain all features."
                ),
                related_object_type="ClinicSubscription",
                related_object_id=str(sub.id),
                action_url="/clinic/subscription",
                force_email=True,
            )
            sub.metadata["trial_warning_sent"] = True
            sub.save(update_fields=["metadata"])
            warning_count += 1

            SubscriptionEvent.objects.create(
                subscription=sub,
                clinic=sub.clinic,
                event_type=SubscriptionEventType.TRIAL_EXPIRING_SOON,
                old_status=sub.status,
                new_status=sub.status,
                reason=f"Trial expiring in {days_left} days. Reminder notification dispatched.",
                metadata={"days_left": days_left},
            )
        except Exception as exc:
            logger.warning("Failed to send trial expiring notice for clinic %s: %s", sub.clinic.name, exc)

    # 2. Elapsed trials (trial_end <= now)
    elapsed_trials = ClinicSubscription.objects.filter(
        status=SubscriptionStatus.TRIALING,
        trial_end__lte=now,
    ).select_related("clinic", "clinic__owner", "plan")

    expired_count = 0
    for sub in elapsed_trials:
        try:
            SubscriptionLifecycleService.expire_subscription(
                subscription=sub,
                reason="14-day free trial period completed without paid upgrade.",
                fallback_to_free=True,
            )
            NotificationService.send_notification(
                recipient=sub.clinic.owner,
                notification_type="SUBSCRIPTION_TRIAL_EXPIRED",
                title="Free Trial Completed",
                message=(
                    f"Your trial for {sub.clinic.name} has concluded. Your facility has been transitioned "
                    "to the Free Community plan. Upgrade anytime to affiliate more doctors and unlock advanced reports."
                ),
                related_object_type="ClinicSubscription",
                related_object_id=str(sub.id),
                action_url="/clinic/subscription",
                force_email=True,
            )
            expired_count += 1
        except Exception as exc:
            logger.error("Error expiring trial for clinic %s: %s", sub.clinic.name, exc)

    logger.info("Processed trial scan: %d warnings sent, %d trials expired.", warning_count, expired_count)
    return {"warnings_sent": warning_count, "trials_expired": expired_count}


@shared_task(name="apps.subscriptions.tasks.check_subscription_renewals_and_expiry_task")
def check_subscription_renewals_and_expiry_task():
    """
    Daily automated scan for paid subscription expirations and grace period handling:
    1. Expires subscriptions scheduled for cancellation whose period has ended.
    2. Expires PAST_DUE subscriptions whose grace period has ended.
    3. Dispatches renewal reminders for active paid plans nearing renewal (3 days).
    """
    now = timezone.now()
    three_days_later = now + timedelta(days=3)

    # 1. Cancelled subscriptions reaching period end
    cancelled_subs = ClinicSubscription.objects.filter(
        status=SubscriptionStatus.CANCELLED,
        cancel_at_period_end=True,
        current_period_end__lte=now,
    ).select_related("clinic", "clinic__owner")

    cancelled_expired = 0
    for sub in cancelled_subs:
        try:
            SubscriptionLifecycleService.expire_subscription(
                subscription=sub,
                reason="Scheduled cancellation period completed.",
                fallback_to_free=True,
            )
            cancelled_expired += 1
        except Exception as exc:
            logger.error("Error expiring cancelled subscription %s: %s", sub.id, exc)

    # 2. Past-due grace periods elapsed
    past_due_subs = ClinicSubscription.objects.filter(
        status=SubscriptionStatus.PAST_DUE,
        grace_period_ends_at__lte=now,
    ).select_related("clinic", "clinic__owner")

    past_due_expired = 0
    for sub in past_due_subs:
        try:
            SubscriptionLifecycleService.expire_subscription(
                subscription=sub,
                reason="Past-due grace period elapsed without successful payment retry.",
                fallback_to_free=True,
            )
            past_due_expired += 1
        except Exception as exc:
            logger.error("Error expiring past due subscription %s: %s", sub.id, exc)

    # 3. Renewal reminders for active subscriptions
    active_renewing_subs = ClinicSubscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=False,
        current_period_end__gt=now,
        current_period_end__lte=three_days_later,
    ).exclude(plan__tier=SubscriptionTier.FREE).select_related("clinic", "clinic__owner", "plan")

    reminders_sent = 0
    for sub in active_renewing_subs:
        if sub.metadata.get(f"renewal_notice_{sub.current_period_end.strftime('%Y%m%d')}"):
            continue
        try:
            days = max(1, (sub.current_period_end - now).days)
            NotificationService.send_notification(
                recipient=sub.clinic.owner,
                notification_type="SUBSCRIPTION_RENEWAL_REMINDER",
                title=f"Subscription Renews in {days} Days",
                message=f"Your {sub.plan.name} subscription for {sub.clinic.name} renews on {sub.current_period_end.strftime('%d %b %Y')}.",
                related_object_type="ClinicSubscription",
                related_object_id=str(sub.id),
                action_url="/clinic/subscription",
            )
            sub.metadata[f"renewal_notice_{sub.current_period_end.strftime('%Y%m%d')}"] = True
            sub.save(update_fields=["metadata"])
            reminders_sent += 1
        except Exception as exc:
            logger.warning("Failed sending renewal notice for %s: %s", sub.clinic.name, exc)

    return {
        "cancelled_expired": cancelled_expired,
        "past_due_expired": past_due_expired,
        "renewal_reminders_sent": reminders_sent,
    }
