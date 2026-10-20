import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class AppointmentStatus(models.TextChoices):
    """Lifecycle status for patient appointments."""
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION", _("Pending Confirmation")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")
    COMPLETED = "COMPLETED", _("Completed")
    NO_SHOW = "NO_SHOW", _("No Show")
    RESCHEDULE_REQUIRED = "RESCHEDULE_REQUIRED", _("Requires Rescheduling")


class Appointment(models.Model):
    """
    Core entity representing a scheduled patient consultation with a doctor at a clinic.
    Enforces tenant boundaries, price snapshotting at booking time, and overlap protection.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(
        _("booking reference"),
        max_length=32,
        unique=True,
        db_index=True,
        help_text=_("Non-sequential, unique public booking reference (e.g. EZD-202610-A1B2C3)."),
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("patient"),
        db_index=True,
    )
    doctor_clinic = models.ForeignKey(
        "clinics.DoctorClinic",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("doctor clinic affiliation"),
        db_index=True,
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("doctor"),
        db_index=True,
        help_text=_("Denormalized for cross-clinic schedule and concurrency checks."),
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("clinic"),
        db_index=True,
        help_text=_("Denormalized for fast clinic scoping and queries."),
    )
    start_at = models.DateTimeField(
        _("appointment start time"),
        db_index=True,
        help_text=_("Timezone-aware start timestamp in UTC."),
    )
    end_at = models.DateTimeField(
        _("appointment end time"),
        db_index=True,
        help_text=_("Timezone-aware end timestamp in UTC."),
    )
    status = models.CharField(
        _("appointment status"),
        max_length=30,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.CONFIRMED,
        db_index=True,
    )
    consultation_fee = models.DecimalField(
        _("consultation fee snapshot"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Immutable snapshot of clinic consultation fee at booking time."),
    )
    currency = models.CharField(
        _("currency"),
        max_length=10,
        default="INR",
        help_text=_("Platform currency code."),
    )
    patient_note = models.TextField(
        _("patient note"),
        blank=True,
        default="",
        max_length=1000,
        help_text=_("Optional note or reason for consultation provided by the patient."),
    )
    cancellation_reason = models.TextField(
        _("cancellation reason"),
        blank=True,
        default="",
        max_length=1000,
        help_text=_("Reason provided when appointment is cancelled or marked for rescheduling."),
    )
    cancelled_at = models.DateTimeField(
        _("cancelled at"),
        null=True,
        blank=True,
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_appointments",
        verbose_name=_("cancelled by"),
    )
    reschedule_required = models.BooleanField(
        _("reschedule required"),
        default=False,
        db_index=True,
        help_text=_("Flag indicating that doctor/clinic unavailability requires this appointment to be rescheduled or cancelled."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "appointments_appointment"
        verbose_name = _("appointment")
        verbose_name_plural = _("appointments")
        ordering = ["-start_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_at__lt=models.F("end_at")),
                name="valid_appointment_interval",
            ),
            models.CheckConstraint(
                condition=models.Q(consultation_fee__gte=Decimal("0.00")),
                name="non_negative_consultation_fee",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor", "start_at"]),
            models.Index(fields=["clinic", "start_at"]),
            models.Index(fields=["patient", "start_at"]),
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["doctor", "status", "start_at"]),
            models.Index(fields=["reschedule_required", "start_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.booking_reference}] {self.patient.email} - Dr. {self.doctor.full_name} @ {self.clinic.name} ({self.status})"

    def clean(self):
        super().clean()
        if self.start_at and self.end_at and self.start_at >= self.end_at:
            raise ValidationError({"end_at": _("Appointment end time must be after start time.")})

    @property
    def duration_minutes(self) -> int:
        if self.start_at and self.end_at:
            return int((self.end_at - self.start_at).total_seconds() // 60)
        return 0

    @property
    def is_blocking(self) -> bool:
        """Determines whether this appointment status blocks other bookings for the same doctor."""
        return self.status in (
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.PENDING_CONFIRMATION,
            AppointmentStatus.COMPLETED,
        )


class AppointmentHistoryEventType(models.TextChoices):
    CREATED = "CREATED", _("Appointment Created")
    PATIENT_CANCELLED = "PATIENT_CANCELLED", _("Patient Cancelled")
    CLINIC_CANCELLED = "CLINIC_CANCELLED", _("Clinic Cancelled")
    DOCTOR_UNAVAILABLE = "DOCTOR_UNAVAILABLE", _("Doctor Unavailability Reported")
    RESCHEDULED = "RESCHEDULED", _("Appointment Rescheduled")
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE", _("Administrative Override")
    COMPLETED = "COMPLETED", _("Completed")
    NO_SHOW = "NO_SHOW", _("No Show")


class AppointmentHistory(models.Model):
    """
    Append-only audit trail recording the full lifecycle and state changes of an appointment.
    Captures actor, reason, timestamps, previous and updated slots, and policy exception flags.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name=_("appointment"),
        db_index=True,
    )
    event_type = models.CharField(
        _("event type"),
        max_length=50,
        choices=AppointmentHistoryEventType.choices,
        db_index=True,
    )
    previous_status = models.CharField(
        _("previous status"),
        max_length=30,
        blank=True,
        default="",
    )
    new_status = models.CharField(
        _("new status"),
        max_length=30,
        blank=True,
        default="",
    )
    previous_start_at = models.DateTimeField(
        _("previous start time"),
        null=True,
        blank=True,
    )
    previous_end_at = models.DateTimeField(
        _("previous end time"),
        null=True,
        blank=True,
    )
    new_start_at = models.DateTimeField(
        _("new start time"),
        null=True,
        blank=True,
    )
    new_end_at = models.DateTimeField(
        _("new end time"),
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_history_entries",
        verbose_name=_("actor"),
    )
    actor_role = models.CharField(
        _("actor role"),
        max_length=30,
        blank=True,
        default="",
    )
    reason = models.TextField(
        _("reason or cancellation note"),
        blank=True,
        default="",
    )
    is_exception = models.BooleanField(
        _("cutoff exception used"),
        default=False,
        help_text=_("Indicates whether this operation bypassed standard cutoff policies."),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(_("timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        db_table = "appointments_history"
        verbose_name = _("appointment history")
        verbose_name_plural = _("appointment histories")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["appointment", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.appointment.booking_reference}: {self.event_type} by {self.actor or 'System'}"


class AppointmentIdempotency(models.Model):
    """
    Guarantees idempotency for appointment booking operations.
    Prevents duplicate bookings caused by network retries or rapid duplicate submissions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_idempotency_records",
        verbose_name=_("patient"),
        db_index=True,
    )
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=128,
        db_index=True,
        help_text=_("Client-supplied or header-provided unique request token."),
    )
    request_hash = models.CharField(
        _("request payload hash"),
        max_length=64,
        help_text=_("SHA-256 hash of canonical booking parameters to detect key reuse with different payload."),
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created appointment"),
    )
    response_status_code = models.PositiveIntegerField(
        _("response HTTP status"),
        default=201,
    )
    response_data = models.JSONField(
        _("persisted response data"),
        default=dict,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "appointments_idempotency"
        verbose_name = _("appointment idempotency record")
        verbose_name_plural = _("appointment idempotency records")
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "idempotency_key"],
                name="unique_patient_booking_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"IdempotencyKey({self.patient.email}, {self.idempotency_key})"
