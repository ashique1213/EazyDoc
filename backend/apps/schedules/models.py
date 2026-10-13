import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Weekday(models.IntegerChoices):
    """
    Standard weekday mapping (0 = Monday ... 6 = Sunday),
    matching Python datetime.weekday() semantics.
    """
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class UnavailabilityReason(models.TextChoices):
    """Reason classifications for doctor leave and unavailable periods."""
    SICK_LEAVE = "SICK_LEAVE", _("Sick Leave")
    EMERGENCY = "EMERGENCY", _("Emergency")
    CONFERENCE = "CONFERENCE", _("Medical Conference")
    PERSONAL = "PERSONAL", _("Personal Leave / Vacation")
    CLINIC_CLOSURE = "CLINIC_CLOSURE", _("Clinic Closure / Maintenance")
    OTHER = "OTHER", _("Other")


class DoctorSchedule(models.Model):
    """
    Represents a recurring working interval for one doctor at one clinic on a specific day of week.
    Schedules belong strictly to a DoctorClinic association, ensuring multi-clinic autonomy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor_clinic = models.ForeignKey(
        "clinics.DoctorClinic",
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("doctor clinic association"),
        db_index=True,
    )
    day_of_week = models.SmallIntegerField(
        _("day of week"),
        choices=Weekday.choices,
        db_index=True,
        help_text=_("0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday"),
    )
    start_time = models.TimeField(_("shift start time"), help_text=_("Start time in clinic operating timezone."))
    end_time = models.TimeField(_("shift end time"), help_text=_("End time in clinic operating timezone."))
    effective_from = models.DateField(
        _("effective from date"),
        null=True,
        blank=True,
        help_text=_("Optional date when this schedule starts being active."),
    )
    effective_until = models.DateField(
        _("effective until date"),
        null=True,
        blank=True,
        help_text=_("Optional date when this schedule ceases to be active."),
    )
    slot_duration_minutes = models.PositiveIntegerField(
        _("slot duration (minutes)"),
        null=True,
        blank=True,
        help_text=_("Optional override of association default appointment duration (5-240 mins)."),
    )
    buffer_minutes = models.PositiveIntegerField(
        _("buffer minutes"),
        default=0,
        help_text=_("Buffer time in minutes after shift or between appointments."),
    )
    max_patients_per_slot = models.PositiveIntegerField(
        _("max patients per slot"),
        default=1,
        help_text=_("Capacity per slot (default 1 for individual consultation)."),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        db_index=True,
        help_text=_("Schedule toggle. Deactivation preserves historical shift records."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "schedules_schedule"
        verbose_name = _("doctor schedule")
        verbose_name_plural = _("doctor schedules")
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_time__lt=models.F("end_time")),
                name="valid_schedule_start_end_time",
            ),
            models.CheckConstraint(
                condition=models.Q(day_of_week__gte=0, day_of_week__lte=6),
                name="valid_schedule_day_of_week",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_duration_minutes__isnull=True)
                | models.Q(slot_duration_minutes__gte=5, slot_duration_minutes__lte=240),
                name="valid_schedule_slot_duration",
            ),
            models.CheckConstraint(
                condition=models.Q(max_patients_per_slot__gte=1),
                name="valid_schedule_max_patients",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor_clinic", "is_active"]),
            models.Index(fields=["day_of_week", "is_active"]),
            models.Index(fields=["doctor_clinic", "day_of_week", "is_active"]),
        ]

    def __str__(self) -> str:
        clinic_name = self.doctor_clinic.clinic.name if self.doctor_clinic_id else "Unknown Clinic"
        doc_name = self.doctor_clinic.doctor.full_name if self.doctor_clinic_id else "Unknown Doctor"
        weekday_name = Weekday(self.day_of_week).label
        return f"{doc_name} @ {clinic_name} - {weekday_name} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    @property
    def weekday(self) -> int:
        """Alias for day_of_week conforming to weekday terminology."""
        return self.day_of_week

    @weekday.setter
    def weekday(self, value: int):
        self.day_of_week = value

    @property
    def effective_slot_duration(self) -> int:
        """Returns specific slot duration override or falls back to doctor-clinic duration."""
        if self.slot_duration_minutes:
            return self.slot_duration_minutes
        if self.doctor_clinic and self.doctor_clinic.appointment_duration_minutes:
            return self.doctor_clinic.appointment_duration_minutes
        return 15

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": _("Shift end time must be strictly after start time.")})
        if self.effective_from and self.effective_until and self.effective_from > self.effective_until:
            raise ValidationError({"effective_until": _("Effective until date must be on or after effective from date.")})
        if self.slot_duration_minutes is not None:
            if self.slot_duration_minutes < 5 or self.slot_duration_minutes > 240:
                raise ValidationError({"slot_duration_minutes": _("Slot duration must be between 5 and 240 minutes.")})


# Schedule alias for backwards/document compatibility
Schedule = DoctorSchedule


class DoctorUnavailability(models.Model):
    """
    Represents time-off, emergency leave, conference, or vacation for a doctor.
    Stored in UTC timezone-aware timestamps.
    If clinic is NULL, the doctor is unavailable across ALL affiliated clinics.
    If clinic is specified, the doctor is unavailable only at that specific clinic.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="unavailabilities",
        verbose_name=_("doctor"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="doctor_unavailabilities",
        verbose_name=_("clinic (optional scope)"),
        db_index=True,
        help_text=_("Leave NULL for global leave across all clinics, or select a specific clinic."),
    )
    start_datetime = models.DateTimeField(
        _("start datetime (UTC)"),
        db_index=True,
        help_text=_("Beginning of unavailability period in UTC."),
    )
    end_datetime = models.DateTimeField(
        _("end datetime (UTC)"),
        db_index=True,
        help_text=_("End of unavailability period in UTC."),
    )
    reason = models.CharField(
        _("reason"),
        max_length=50,
        choices=UnavailabilityReason.choices,
        default=UnavailabilityReason.PERSONAL,
    )
    notes = models.TextField(_("internal notes"), blank=True, default="")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "schedules_doctorunavailability"
        verbose_name = _("doctor unavailability")
        verbose_name_plural = _("doctor unavailabilities")
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_datetime__lt=models.F("end_datetime")),
                name="valid_unavailability_datetimes",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor", "start_datetime"]),
            models.Index(fields=["clinic", "start_datetime"]),
            models.Index(fields=["start_datetime", "end_datetime"]),
        ]

    def __str__(self) -> str:
        doc_name = self.doctor.full_name if self.doctor_id else "Doctor"
        scope = self.clinic.name if self.clinic_id else "All Clinics"
        return f"{doc_name} Leave: {self.start_datetime.strftime('%Y-%m-%d %H:%M')} to {self.end_datetime.strftime('%Y-%m-%d %H:%M')} ({scope})"

    def clean(self):
        super().clean()
        if self.start_datetime and self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError({"end_datetime": _("End datetime must be strictly after start datetime.")})


class BlockedSlot(models.Model):
    """
    Represents an ad-hoc administrative block on a specific date and time slot
    for a doctor at a specific clinic (e.g. VIP reservation, clinic inspection, equipment repair).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor_clinic = models.ForeignKey(
        "clinics.DoctorClinic",
        on_delete=models.CASCADE,
        related_name="blocked_slots",
        verbose_name=_("doctor clinic association"),
        db_index=True,
    )
    date = models.DateField(_("blocked date"), db_index=True)
    start_time = models.TimeField(_("blocked slot start time"))
    end_time = models.TimeField(
        _("blocked slot end time"),
        null=True,
        blank=True,
        help_text=_("Optional slot end time. If null, calculated from slot duration."),
    )
    reason = models.CharField(_("reason for blocking"), max_length=255, blank=True, default="")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "schedules_blockedslot"
        verbose_name = _("blocked slot")
        verbose_name_plural = _("blocked slots")
        ordering = ["date", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor_clinic", "date", "start_time"],
                name="unique_doctor_clinic_date_start_time",
            ),
        ]
        indexes = [
            models.Index(fields=["doctor_clinic", "date"]),
            models.Index(fields=["date", "start_time"]),
        ]

    def __str__(self) -> str:
        doc_name = self.doctor_clinic.doctor.full_name if self.doctor_clinic_id else "Doctor"
        clinic_name = self.doctor_clinic.clinic.name if self.doctor_clinic_id else "Clinic"
        return f"Blocked: {doc_name} @ {clinic_name} on {self.date} at {self.start_time.strftime('%H:%M')}"
