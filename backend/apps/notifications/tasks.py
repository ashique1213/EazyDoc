import logging
from datetime import timedelta
from zoneinfo import ZoneInfo
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    AppointmentReminderSchedule,
    DeliveryStatus,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationType,
)

logger = logging.getLogger("apps.notifications")


TEMPLATE_MAPPING = {
    NotificationType.APPOINTMENT_CONFIRMED: ("emails/appointment_confirmed.txt", "emails/appointment_confirmed.html"),
    NotificationType.APPOINTMENT_REMINDER: ("emails/appointment_reminder.txt", "emails/appointment_reminder.html"),
    NotificationType.APPOINTMENT_CANCELLED: ("emails/appointment_cancelled.txt", "emails/appointment_cancelled.html"),
    NotificationType.APPOINTMENT_RESCHEDULED: ("emails/appointment_rescheduled.txt", "emails/appointment_rescheduled.html"),
    NotificationType.PAYMENT_VERIFIED: ("emails/payment_verified.txt", "emails/payment_verified.html"),
    NotificationType.PAYMENT_FAILED: ("emails/payment_failed.txt", "emails/payment_failed.html"),
    NotificationType.DOCTOR_UNAVAILABLE: ("emails/doctor_unavailability.txt", "emails/doctor_unavailability.html"),
    NotificationType.CLINIC_CLOSURE: ("emails/doctor_unavailability.txt", "emails/doctor_unavailability.html"),
    NotificationType.CLINIC_INVITATION_SENT: ("emails/clinic_invitation.txt", "emails/clinic_invitation.html"),
}


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_email_notification_task(self, delivery_id: str):
    """
    Celery task to asynchronously deliver an email notification.
    Enforces idempotency, bounded exponential backoff retries for transient failures,
    and sanitized failure logging without exposing sensitive data.
    """
    try:
        delivery = NotificationDelivery.objects.select_related("notification", "notification__recipient").get(id=delivery_id)
    except NotificationDelivery.DoesNotExist:
        logger.warning("NotificationDelivery %s does not exist; skipping task.", delivery_id)
        return "Delivery record not found"

    # Idempotent guard
    if delivery.status in (DeliveryStatus.SENT, DeliveryStatus.CANCELLED):
        logger.info("Delivery %s is already in terminal state %s; skipping.", delivery_id, delivery.status)
        return f"Already {delivery.status}"

    # Atomic progress mark
    with transaction.atomic():
        delivery.attempt_count += 1
        delivery.last_attempt_at = timezone.now()
        delivery.status = DeliveryStatus.PROCESSING
        delivery.save(update_fields=["attempt_count", "last_attempt_at", "status", "updated_at"])

    notification = delivery.notification
    recipient = notification.recipient
    recipient_email = getattr(recipient, "email", "").strip()

    # Permanent failure validation
    if not recipient_email or "@" not in recipient_email:
        with transaction.atomic():
            delivery.status = DeliveryStatus.FAILED
            delivery.sanitized_failure_reason = "Recipient does not possess a valid email address."
            delivery.save(update_fields=["status", "sanitized_failure_reason", "updated_at"])
        logger.warning("Permanent failure for delivery %s: invalid email.", delivery_id)
        return "Invalid recipient email"

    # Determine templates
    txt_tmpl, html_tmpl = TEMPLATE_MAPPING.get(
        notification.notification_type,
        ("emails/generic_notification.txt", "emails/generic_notification.html"),
    )

    context = {
        "title": notification.title,
        "message": notification.message,
        "action_url": notification.action_url,
        "recipient_name": str(recipient),
        "current_year": timezone.now().year,
        "booking_reference": getattr(notification, "_booking_reference", "") or notification.related_object_id,
        "clinic_name": getattr(notification, "_clinic_name", ""),
        "doctor_name": getattr(notification, "_doctor_name", ""),
        "scheduled_time": getattr(notification, "_scheduled_time", ""),
        "clinic_timezone": getattr(notification, "_clinic_timezone", "Asia/Kolkata"),
    }

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@eazydoc.com")

    try:
        text_body = render_to_string(txt_tmpl, context)
        html_body = render_to_string(html_tmpl, context)

        email_message = EmailMultiAlternatives(
            subject=notification.title,
            body=text_body,
            from_email=from_email,
            to=[recipient_email],
        )
        email_message.attach_alternative(html_body, "text/html")
        email_message.send(fail_silently=False)

        with transaction.atomic():
            delivery.status = DeliveryStatus.SENT
            delivery.sent_at = timezone.now()
            delivery.sanitized_failure_reason = ""
            delivery.save(update_fields=["status", "sent_at", "sanitized_failure_reason", "updated_at"])

        logger.info("Successfully delivered email notification %s to recipient %s", delivery_id, recipient.id)
        return "Delivered"

    except Exception as exc:
        sanitized_reason = f"{exc.__class__.__name__}: {str(exc)}"[:250]
        logger.error(
            "Transient failure delivering email %s on attempt %d: %s",
            delivery_id,
            delivery.attempt_count,
            sanitized_reason,
        )

        if self.request.retries >= self.max_retries:
            with transaction.atomic():
                delivery.status = DeliveryStatus.FAILED
                delivery.sanitized_failure_reason = f"Max retries exceeded: {sanitized_reason}"
                delivery.save(update_fields=["status", "sanitized_failure_reason", "updated_at"])
            return f"Permanent failure: {sanitized_reason}"

        # Bounded exponential backoff: 5s, 10s, 20s
        countdown = 5 * (2 ** self.request.retries)
        with transaction.atomic():
            delivery.sanitized_failure_reason = f"Retry scheduled: {sanitized_reason}"
            delivery.save(update_fields=["sanitized_failure_reason", "updated_at"])

        raise self.retry(exc=exc, countdown=countdown)


@shared_task(name="apps.notifications.tasks.process_due_appointment_reminders")
def process_due_appointment_reminders():
    """
    Periodic Celery Beat task to process due upcoming appointment reminders.
    Finds pending reminder schedules whose due timestamp has arrived,
    re-verifies appointment validity and recipient preferences immediately before delivery,
    and records outcomes idempotently.
    """
    from apps.appointments.models import AppointmentStatus
    from .services import NotificationService

    now = timezone.now()
    due_schedules = (
        AppointmentReminderSchedule.objects.select_for_update(skip_locked=True)
        .filter(status="PENDING", scheduled_for__lte=now)
        .select_related("appointment", "appointment__patient", "appointment__doctor", "appointment__clinic")[:100]
    )

    processed_count = 0
    with transaction.atomic():
        for reminder_schedule in due_schedules:
            appointment = reminder_schedule.appointment

            # Recheck appointment status
            if appointment.status != AppointmentStatus.CONFIRMED or appointment.reschedule_required:
                reminder_schedule.status = "CANCELLED"
                reminder_schedule.save(update_fields=["status", "updated_at"])
                continue

            # Recheck if appointment start_at has already passed
            if appointment.start_at <= now:
                reminder_schedule.status = "SKIPPED"
                reminder_schedule.save(update_fields=["status", "updated_at"])
                continue

            patient = appointment.patient
            prefs = NotificationPreference.get_for_user(patient)

            if not prefs.appointment_reminders_enabled:
                reminder_schedule.status = "SKIPPED"
                reminder_schedule.save(update_fields=["status", "updated_at"])
                continue

            # Format clinic local time safely
            clinic_tz_name = getattr(appointment.clinic, "timezone", "Asia/Kolkata") or "Asia/Kolkata"
            try:
                local_start = appointment.start_at.astimezone(ZoneInfo(clinic_tz_name))
            except Exception:
                local_start = appointment.start_at

            time_str = local_start.strftime("%A, %d %B %Y at %I:%M %p")
            timing_label = "24 hours" if "24H" in reminder_schedule.reminder_type else "2 hours"

            # Create notification
            notification = NotificationService.send_notification(
                recipient=patient,
                notification_type=NotificationType.APPOINTMENT_REMINDER,
                title="Upcoming Appointment Reminder - EazyDoc",
                message=(
                    f"Reminder: You have an upcoming consultation with Dr. {appointment.doctor.full_name} "
                    f"at {appointment.clinic.name} scheduled for {time_str}."
                ),
                related_object_type="appointment",
                related_object_id=str(appointment.id),
                action_url=f"/appointments/{appointment.id}",
                idempotency_key=f"reminder_{reminder_schedule.id}",
                extra_context={
                    "_booking_reference": appointment.booking_reference,
                    "_clinic_name": appointment.clinic.name,
                    "_doctor_name": appointment.doctor.full_name,
                    "_scheduled_time": time_str,
                    "_clinic_timezone": clinic_tz_name,
                },
            )

            reminder_schedule.status = "SENT"
            reminder_schedule.sent_at = now
            reminder_schedule.notification = notification
            reminder_schedule.save(update_fields=["status", "sent_at", "notification", "updated_at"])
            processed_count += 1

    logger.info("Processed %d due appointment reminders at %s", processed_count, now.isoformat())
    return processed_count
