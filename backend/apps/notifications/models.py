import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    """Controlled set of system notification types."""
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED", _("Appointment Confirmed")
    APPOINTMENT_PENDING = "APPOINTMENT_PENDING", _("Appointment Pending Confirmation")
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", _("Upcoming Appointment Reminder")
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", _("Appointment Cancelled")
    APPOINTMENT_RESCHEDULED = "APPOINTMENT_RESCHEDULED", _("Appointment Rescheduled")
    DOCTOR_UNAVAILABLE = "DOCTOR_UNAVAILABLE", _("Doctor Unavailability Reported")
    CLINIC_CLOSURE = "CLINIC_CLOSURE", _("Clinic Closure")
    APPOINTMENT_REQUIRES_ATTENTION = "APPOINTMENT_REQUIRES_ATTENTION", _("Appointment Requires Attention")
    APPOINTMENT_COMPLETED = "APPOINTMENT_COMPLETED", _("Appointment Completed")
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED", _("Payment Verified")
    PAYMENT_FAILED = "PAYMENT_FAILED", _("Payment Failed")
    PAYMENT_PENDING = "PAYMENT_PENDING", _("Payment Action Required")
    PAYMENT_ISSUE = "PAYMENT_ISSUE", _("Payment Issue")
    CLINIC_INVITATION_SENT = "CLINIC_INVITATION_SENT", _("Clinic Invitation Received")
    CLINIC_INVITATION_ACCEPTED = "CLINIC_INVITATION_ACCEPTED", _("Clinic Invitation Accepted")
    CLINIC_INVITATION_REJECTED = "CLINIC_INVITATION_REJECTED", _("Clinic Invitation Rejected")


class NotificationChannel(models.TextChoices):
    """Delivery channels supported or extensible in the notification system."""
    IN_APP = "IN_APP", _("In-App")
    EMAIL = "EMAIL", _("Email")
    SMS = "SMS", _("SMS")
    WHATSAPP = "WHATSAPP", _("WhatsApp")


class DeliveryStatus(models.TextChoices):
    """Status lifecycle for channel-specific message delivery."""
    PENDING = "PENDING", _("Pending")
    PROCESSING = "PROCESSING", _("Processing")
    SENT = "SENT", _("Sent")
    FAILED = "FAILED", _("Failed")
    CANCELLED = "CANCELLED", _("Cancelled")


class Notification(models.Model):
    """
    In-app user notification entity.
    Scoped strictly to the authenticated recipient. Avoids storing sensitive medical details
    or full appointment snapshots.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient"),
        db_index=True,
    )
    notification_type = models.CharField(
        _("notification type"),
        max_length=64,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(_("title"), max_length=255)
    message = models.TextField(_("message"))
    related_object_type = models.CharField(
        _("related object type"),
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text=_("e.g. appointment, payment, doctor_clinic"),
    )
    related_object_id = models.CharField(
        _("related object ID"),
        max_length=64,
        blank=True,
        default="",
        db_index=True,
    )
    action_url = models.CharField(
        _("action URL"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Safe relative in-app URL linking to relevant page."),
    )
    is_read = models.BooleanField(_("is read"), default=False, db_index=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Notification({self.recipient.email}, {self.notification_type}, read={self.is_read})"

    def mark_as_read(self) -> None:
        """Marks the notification as read if not already marked."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationDelivery(models.Model):
    """
    Tracks channel-specific delivery attempts separately from the in-app notification record.
    Provides idempotent tracking, failure logs, and retry attempts for background Celery workers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("notification"),
        db_index=True,
    )
    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=NotificationChannel.choices,
        db_index=True,
    )
    status = models.CharField(
        _("delivery status"),
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    attempt_count = models.PositiveIntegerField(_("attempt count"), default=0)
    last_attempt_at = models.DateTimeField(_("last attempt timestamp"), null=True, blank=True)
    sent_at = models.DateTimeField(_("sent timestamp"), null=True, blank=True)
    sanitized_failure_reason = models.TextField(_("sanitized failure reason"), blank=True, default="")
    provider_message_id = models.CharField(_("provider message ID"), max_length=255, blank=True, default="")
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Prevents concurrent duplicate delivery tasks."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "notifications_delivery"
        verbose_name = _("notification delivery")
        verbose_name_plural = _("notification deliveries")
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self) -> str:
        return f"Delivery({self.notification_id}, {self.channel}, {self.status}, attempts={self.attempt_count})"


class NotificationPreference(models.Model):
    """
    User-configurable notification channel and category preferences.
    Distinguishes operational & security messages (always delivered) from optional reminders.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name=_("user"),
        db_index=True,
    )
    email_enabled = models.BooleanField(_("email enabled"), default=True)
    in_app_enabled = models.BooleanField(_("in-app enabled"), default=True)
    appointment_reminders_enabled = models.BooleanField(_("appointment reminders enabled"), default=True)
    appointment_updates_enabled = models.BooleanField(_("appointment updates enabled"), default=True)
    payment_updates_enabled = models.BooleanField(_("payment updates enabled"), default=True)
    clinic_announcements_enabled = models.BooleanField(_("clinic announcements enabled"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "notifications_preference"
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")

    def __str__(self) -> str:
        return f"Preferences({self.user.email}, email={self.email_enabled}, in_app={self.in_app_enabled})"

    @classmethod
    def get_for_user(cls, user) -> "NotificationPreference":
        """Retrieves or lazily initializes default preferences for a user."""
        pref, _ = cls.objects.get_or_create(user=user)
        return pref


class AppointmentReminderSchedule(models.Model):
    """
    Tracks scheduled upcoming appointment reminders, schedule versions, and delivery outcomes.
    Ensures repeated Celery Beat runs do not duplicate reminders and invalidates pending reminders
    when an appointment is rescheduled or cancelled.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="reminder_schedules",
        verbose_name=_("appointment"),
        db_index=True,
    )
    reminder_type = models.CharField(
        _("reminder type"),
        max_length=32,
        db_index=True,
        help_text=_("e.g. REMINDER_24H, REMINDER_2H"),
    )
    scheduled_for = models.DateTimeField(
        _("scheduled for (UTC)"),
        db_index=True,
        help_text=_("Timestamp when reminder is due in UTC."),
    )
    schedule_version = models.PositiveIntegerField(
        _("schedule version"),
        default=1,
        help_text=_("Tracks appointment schedule version; invalidated on reschedule."),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=[
            ("PENDING", _("Pending")),
            ("SENT", _("Sent")),
            ("CANCELLED", _("Cancelled")),
            ("SKIPPED", _("Skipped")),
        ],
        default="PENDING",
        db_index=True,
    )
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_reminders",
        verbose_name=_("generated notification"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "notifications_reminderschedule"
        verbose_name = _("appointment reminder schedule")
        verbose_name_plural = _("appointment reminder schedules")
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "reminder_type", "schedule_version"],
                name="unique_appointment_reminder_version",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["appointment", "status"]),
        ]

    def __str__(self) -> str:
        return f"ReminderSchedule({self.appointment_id}, {self.reminder_type}, v{self.schedule_version}, {self.status})"
