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
