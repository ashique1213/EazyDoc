import logging
from datetime import timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    AppointmentReminderSchedule,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationType,
)
from .tasks import send_email_notification_task

logger = logging.getLogger("apps.notifications")


class NotificationService:
    """
    Centralized, multi-channel notification engine.
    Dispatches in-app and email notifications respecting user preferences and recipient privacy rules.
    Extensible for SMS and WhatsApp channels.
    """

    @classmethod
    def send_notification(
        cls,
        recipient: Any,
        notification_type: str,
        title: str,
        message: str,
        related_object_type: str = "",
        related_object_id: str = "",
        action_url: str = "",
        idempotency_key: str = "",
        extra_context: Optional[Dict[str, Any]] = None,
        force_email: bool = False,
    ) -> Optional[Notification]:
        """
        Sends an in-app and/or email notification to an authorized recipient.
        Guarantees idempotency and respects recipient preferences.
        """
        if not recipient:
            logger.warning("Attempted to send notification without a valid recipient.")
            return None

        # Resolve preferences
        prefs = NotificationPreference.get_for_user(recipient)

        # Check category preferences
        if notification_type == NotificationType.APPOINTMENT_REMINDER and not prefs.appointment_reminders_enabled:
            logger.info("Skipping reminder for user %s per preferences.", recipient.id)
            return None

        if (
            notification_type
            in (
                NotificationType.APPOINTMENT_CANCELLED,
                NotificationType.APPOINTMENT_RESCHEDULED,
                NotificationType.APPOINTMENT_CONFIRMED,
            )
            and not prefs.appointment_updates_enabled
        ):
            # Optional appointment updates disabled
            logger.info("Skipping optional appointment update for user %s per preferences.", recipient.id)
            return None

        if (
            notification_type in (NotificationType.PAYMENT_VERIFIED, NotificationType.PAYMENT_FAILED)
            and not prefs.payment_updates_enabled
            and not force_email
        ):
            logger.info("Skipping payment update for user %s per preferences.", recipient.id)
            return None

        # Check idempotency if key provided
        if idempotency_key:
            existing_delivery = NotificationDelivery.objects.filter(
                idempotency_key=f"{idempotency_key}_in_app"
            ).first()
            if existing_delivery:
                logger.info("Duplicate notification ignored for idempotency key %s", idempotency_key)
                return existing_delivery.notification

        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                related_object_type=related_object_type,
                related_object_id=str(related_object_id),
                action_url=action_url,
            )

            # Store extra context on transient attributes for email templating
            if extra_context:
                for k, v in extra_context.items():
                    setattr(notification, k, v)

            # 1. In-App delivery
            if prefs.in_app_enabled:
                NotificationDelivery.objects.create(
                    notification=notification,
                    channel=NotificationChannel.IN_APP,
                    status=DeliveryStatus.SENT,
                    attempt_count=1,
                    sent_at=timezone.now(),
                    idempotency_key=f"{idempotency_key}_in_app" if idempotency_key else "",
                )

            # 2. Email delivery
            should_send_email = (prefs.email_enabled or force_email) and getattr(recipient, "email", None)
            if should_send_email:
                email_delivery = NotificationDelivery.objects.create(
                    notification=notification,
                    channel=NotificationChannel.EMAIL,
                    status=DeliveryStatus.PENDING,
                    attempt_count=0,
                    idempotency_key=f"{idempotency_key}_email" if idempotency_key else "",
                )
                delivery_id = str(email_delivery.id)
                transaction.on_commit(lambda: send_email_notification_task.delay(delivery_id))

        return notification


def format_clinic_datetime(dt, timezone_name: Optional[str] = None) -> str:
    """Formats a timezone-aware datetime using the clinic's local timezone."""
    tz_str = timezone_name or "Asia/Kolkata"
    try:
        local_dt = dt.astimezone(ZoneInfo(tz_str))
    except Exception:
        local_dt = dt
    return local_dt.strftime("%A, %d %B %Y at %I:%M %p")


def schedule_appointment_reminders(appointment, schedule_version: int = 1) -> None:
    """
    Schedules due reminder windows (e.g. 24h, 2h before start) for an appointment.
    Skips reminder windows that are already in the past.
    """
    now = timezone.now()
    reminder_windows = getattr(settings, "NOTIFICATION_REMINDER_WINDOWS", [
        {"type": "REMINDER_24H", "offset_hours": 24},
        {"type": "REMINDER_2H", "offset_hours": 2},
    ])

    for window in reminder_windows:
        win_type = window["type"]
        offset_hours = window["offset_hours"]
        due_timestamp = appointment.start_at - timedelta(hours=offset_hours)

        status = "SKIPPED" if due_timestamp <= now else "PENDING"

        AppointmentReminderSchedule.objects.get_or_create(
            appointment=appointment,
            reminder_type=win_type,
            schedule_version=schedule_version,
            defaults={
                "scheduled_for": due_timestamp,
                "status": status,
            },
        )


def invalidate_appointment_reminders(appointment) -> None:
    """Cancels any pending reminder schedules for an appointment."""
    AppointmentReminderSchedule.objects.filter(
        appointment=appointment,
        status="PENDING",
    ).update(status="CANCELLED", updated_at=timezone.now())


def reschedule_appointment_reminders(appointment) -> None:
    """
    Invalidates existing reminders and schedules new reminder windows
    with an incremented schedule version.
    """
    invalidate_appointment_reminders(appointment)
    latest = (
        AppointmentReminderSchedule.objects.filter(appointment=appointment)
        .order_by("-schedule_version")
        .first()
    )
    next_version = (latest.schedule_version + 1) if latest else 2
    schedule_appointment_reminders(appointment, schedule_version=next_version)


def handle_appointment_event(event_name: str, appointment_id: Any, **kwargs) -> None:
    """
    Dispatches notifications for appointment lifecycle events:
    - appointment_created (confirmed / pending)
    - appointment_cancelled
    - appointment_rescheduled
    - doctor_unavailability_reported
    """
    from apps.appointments.models import Appointment, AppointmentStatus

    try:
        appointment = (
            Appointment.objects.select_related("patient", "doctor", "doctor__user", "clinic", "clinic__owner")
            .get(id=appointment_id)
        )
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for event dispatch '%s'", appointment_id, event_name)
        return

    clinic_tz = getattr(appointment.clinic, "timezone", "Asia/Kolkata") or "Asia/Kolkata"
    start_str = format_clinic_datetime(appointment.start_at, clinic_tz)
    patient = appointment.patient
    doctor = appointment.doctor
    doctor_user = getattr(doctor, "user", None)
    clinic_owner = getattr(appointment.clinic, "owner", None)

    context_common = {
        "_booking_reference": appointment.booking_reference,
        "_clinic_name": appointment.clinic.name,
        "_doctor_name": doctor.full_name,
        "_scheduled_time": start_str,
        "_clinic_timezone": clinic_tz,
    }

    if event_name in ("appointment_created", "appointment_confirmed"):
        if appointment.status == AppointmentStatus.CONFIRMED:
            # Schedule reminders
            schedule_appointment_reminders(appointment, schedule_version=1)

            # Notify patient
            NotificationService.send_notification(
                recipient=patient,
                notification_type=NotificationType.APPOINTMENT_CONFIRMED,
                title="Appointment Confirmed - EazyDoc",
                message=(
                    f"Your consultation with Dr. {doctor.full_name} at {appointment.clinic.name} "
                    f"has been successfully confirmed for {start_str}. Booking ref: {appointment.booking_reference}."
                ),
                related_object_type="appointment",
                related_object_id=str(appointment.id),
                action_url=f"/appointments/{appointment.id}",
                idempotency_key=f"appt_confirmed_patient_{appointment.id}",
                extra_context=context_common,
            )

            # Notify doctor if registered
            if doctor_user:
                NotificationService.send_notification(
                    recipient=doctor_user,
                    notification_type=NotificationType.APPOINTMENT_CONFIRMED,
                    title="New Appointment Scheduled - EazyDoc",
                    message=(
                        f"A new consultation has been booked with patient {patient} "
                        f"on {start_str} at {appointment.clinic.name}. Booking ref: {appointment.booking_reference}."
                    ),
                    related_object_type="appointment",
                    related_object_id=str(appointment.id),
                    action_url="/doctor/schedules",
                    idempotency_key=f"appt_confirmed_doc_{appointment.id}",
                    extra_context=context_common,
                )

    elif event_name == "appointment_cancelled":
        invalidate_appointment_reminders(appointment)
        reason = kwargs.get("reason", "") or appointment.cancellation_reason or "Cancellation requested."

        # Notify patient
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.APPOINTMENT_CANCELLED,
            title="Appointment Cancelled - EazyDoc",
            message=(
                f"Your appointment with Dr. {doctor.full_name} scheduled for {start_str} "
                f"at {appointment.clinic.name} has been cancelled. Reason: {reason}"
            ),
            related_object_type="appointment",
            related_object_id=str(appointment.id),
            action_url=f"/appointments/{appointment.id}",
            idempotency_key=f"appt_cancelled_patient_{appointment.id}",
            extra_context={**context_common, "reason": reason},
        )

        # Notify doctor
        if doctor_user:
            NotificationService.send_notification(
                recipient=doctor_user,
                notification_type=NotificationType.APPOINTMENT_CANCELLED,
                title="Appointment Cancelled - EazyDoc",
                message=(
                    f"Appointment with patient {patient} "
                    f"on {start_str} at {appointment.clinic.name} has been cancelled. Reason: {reason}"
                ),
                related_object_type="appointment",
                related_object_id=str(appointment.id),
                action_url="/doctor/schedules",
                idempotency_key=f"appt_cancelled_doc_{appointment.id}",
                extra_context={**context_common, "reason": reason},
            )

    elif event_name == "appointment_rescheduled":
        reschedule_appointment_reminders(appointment)

        # Notify patient
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.APPOINTMENT_RESCHEDULED,
            title="Appointment Rescheduled - EazyDoc",
            message=(
                f"Your appointment with Dr. {doctor.full_name} has been rescheduled to {start_str} "
                f"at {appointment.clinic.name}."
            ),
            related_object_type="appointment",
            related_object_id=str(appointment.id),
            action_url=f"/appointments/{appointment.id}",
            idempotency_key=f"appt_rescheduled_patient_{appointment.id}_{appointment.start_at.isoformat()}",
            extra_context=context_common,
        )

        # Notify doctor
        if doctor_user:
            NotificationService.send_notification(
                recipient=doctor_user,
                notification_type=NotificationType.APPOINTMENT_RESCHEDULED,
                title="Appointment Rescheduled - EazyDoc",
                message=(
                    f"Appointment with patient {patient} has been rescheduled "
                    f"to {start_str} at {appointment.clinic.name}."
                ),
                related_object_type="appointment",
                related_object_id=str(appointment.id),
                action_url="/doctor/schedules",
                idempotency_key=f"appt_rescheduled_doc_{appointment.id}_{appointment.start_at.isoformat()}",
                extra_context=context_common,
            )

    elif event_name == "doctor_unavailability_reported":
        invalidate_appointment_reminders(appointment)
        reason = kwargs.get("reason", "Doctor reported unavailability.")

        # Notify patient
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.DOCTOR_UNAVAILABLE,
            title="Schedule Disruption Notice - EazyDoc",
            message=(
                f"Notice: Dr. {doctor.full_name} has reported unavailability affecting your appointment "
                f"scheduled for {start_str}. Please review rescheduling options in your portal."
            ),
            related_object_type="appointment",
            related_object_id=str(appointment.id),
            action_url=f"/appointments/{appointment.id}",
            idempotency_key=f"unavail_patient_{appointment.id}",
            extra_context={**context_common, "reason": reason},
        )

        # Notify clinic owner/staff
        if clinic_owner:
            NotificationService.send_notification(
                recipient=clinic_owner,
                notification_type=NotificationType.DOCTOR_UNAVAILABLE,
                title="Staff Action Required: Doctor Unavailability - EazyDoc",
                message=(
                    f"Dr. {doctor.full_name} is unavailable for appointment {appointment.booking_reference} "
                    f"on {start_str}. Patient attention required."
                ),
                related_object_type="appointment",
                related_object_id=str(appointment.id),
                action_url=f"/clinic/appointments",
                idempotency_key=f"unavail_clinic_{appointment.id}",
                extra_context={**context_common, "reason": reason},
            )


def handle_payment_event(event_name: str, payment_id: Any, **kwargs) -> None:
    """
    Dispatches notifications for payment verification, failure, and discrepancy events.
    Enforces idempotency to avoid duplicate notifications between frontend callbacks and webhooks.
    """
    from apps.payments.models import Payment

    try:
        payment = (
            Payment.objects.select_related("patient", "clinic", "clinic__owner", "appointment", "appointment__doctor")
            .get(id=payment_id)
        )
    except Payment.DoesNotExist:
        logger.warning("Payment %s not found for event dispatch '%s'", payment_id, event_name)
        return

    patient = payment.patient
    clinic_owner = getattr(payment.clinic, "owner", None)
    appt = payment.appointment

    extra_context = {
        "_booking_reference": appt.booking_reference if appt else "",
        "amount": str(payment.amount),
        "currency": payment.currency or "INR",
        "order_id": payment.gateway_order_id,
        "failure_reason": kwargs.get("error_desc", payment.failure_description) or "Payment could not be completed.",
    }

    if event_name == "payment_verified":
        # 1. Notify patient
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.PAYMENT_VERIFIED,
            title="Payment Verified - EazyDoc",
            message=(
                f"Your payment of {payment.currency} {payment.amount} has been verified successfully. "
                f"Booking reference: {appt.booking_reference if appt else 'N/A'}."
            ),
            related_object_type="payment",
            related_object_id=str(payment.id),
            action_url=f"/appointments/{appt.id}" if appt else "/patient",
            idempotency_key=f"pay_verified_patient_{payment.id}",
            extra_context=extra_context,
        )

        # 2. Notify clinic owner (without revealing platform commission information to patient)
        if clinic_owner:
            NotificationService.send_notification(
                recipient=clinic_owner,
                notification_type=NotificationType.PAYMENT_VERIFIED,
                title="Payment Received - EazyDoc",
                message=(
                    f"A consultation payment of {payment.currency} {payment.amount} was received "
                    f"for {payment.clinic.name} (Booking: {appt.booking_reference if appt else 'N/A'})."
                ),
                related_object_type="payment",
                related_object_id=str(payment.id),
                action_url="/clinic/finance",
                idempotency_key=f"pay_verified_clinic_{payment.id}",
                extra_context=extra_context,
            )

    elif event_name == "payment_failed":
        reason = kwargs.get("error_desc", "") or payment.failure_description or "Payment was declined by payment gateway."
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.PAYMENT_FAILED,
            title="Payment Failed - EazyDoc",
            message=(
                f"Payment for booking {appt.booking_reference if appt else 'N/A'} could not be completed. "
                f"Reason: {reason}"
            ),
            related_object_type="payment",
            related_object_id=str(payment.id),
            action_url=f"/appointments/{appt.id}" if appt else "/patient",
            idempotency_key=f"pay_failed_patient_{payment.id}",
            extra_context=extra_context,
        )

    elif event_name == "payment_issue":
        NotificationService.send_notification(
            recipient=patient,
            notification_type=NotificationType.PAYMENT_ISSUE,
            title="Payment Issue Requiring Attention - EazyDoc",
            message=(
                f"Your payment was received after the booking window expired. "
                f"Please review your booking {appt.booking_reference if appt else ''} to select a new slot or refund."
            ),
            related_object_type="appointment",
            related_object_id=str(appt.id) if appt else str(payment.id),
            action_url=f"/appointments/{appt.id}" if appt else "/patient",
            idempotency_key=f"pay_issue_patient_{payment.id}",
            extra_context=extra_context,
        )


def handle_clinic_doctor_event(event_name: str, association_id: Any, **kwargs) -> None:
    """
    Dispatches notifications for doctor-clinic invitations:
    - clinic_invitation_sent
    - clinic_invitation_accepted
    - clinic_invitation_rejected
    """
    from apps.clinics.models import DoctorClinic

    try:
        assoc = (
            DoctorClinic.objects.select_related("doctor", "doctor__user", "clinic", "clinic__owner", "invited_by")
            .get(id=association_id)
        )
    except DoctorClinic.DoesNotExist:
        logger.warning("DoctorClinic %s not found for event '%s'", association_id, event_name)
        return

    doctor = assoc.doctor
    doctor_user = getattr(doctor, "user", None)
    clinic = assoc.clinic
    clinic_owner = clinic.owner

    extra_context = {
        "clinic_name": clinic.name,
        "clinic_address": clinic.address_line_1 or "",
        "invited_by_name": str(assoc.invited_by) if assoc.invited_by else clinic.name,
        "doctor_name": doctor.full_name,
    }

    if event_name == "clinic_invitation_sent":
        if doctor_user:
            NotificationService.send_notification(
                recipient=doctor_user,
                notification_type=NotificationType.CLINIC_INVITATION_SENT,
                title="Clinic Practice Invitation - EazyDoc",
                message=(
                    f"You have received an invitation from {clinic.name} to join their clinical practice. "
                    f"Please review and accept or decline."
                ),
                related_object_type="doctor_clinic",
                related_object_id=str(assoc.id),
                action_url="/doctor/clinics",
                idempotency_key=f"invitation_sent_{assoc.id}",
                extra_context=extra_context,
            )

    elif event_name == "clinic_invitation_accepted":
        if clinic_owner:
            NotificationService.send_notification(
                recipient=clinic_owner,
                notification_type=NotificationType.CLINIC_INVITATION_ACCEPTED,
                title="Doctor Accepted Invitation - EazyDoc",
                message=f"Dr. {doctor.full_name} has accepted your invitation to join {clinic.name}.",
                related_object_type="doctor_clinic",
                related_object_id=str(assoc.id),
                action_url="/clinic/doctors",
                idempotency_key=f"invitation_accepted_{assoc.id}",
                extra_context=extra_context,
            )

    elif event_name == "clinic_invitation_rejected":
        if clinic_owner:
            NotificationService.send_notification(
                recipient=clinic_owner,
                notification_type=NotificationType.CLINIC_INVITATION_REJECTED,
                title="Doctor Declined Invitation - EazyDoc",
                message=f"Dr. {doctor.full_name} has declined your invitation to join {clinic.name}.",
                related_object_type="doctor_clinic",
                related_object_id=str(assoc.id),
                action_url="/clinic/doctors",
                idempotency_key=f"invitation_rejected_{assoc.id}",
                extra_context=extra_context,
            )
