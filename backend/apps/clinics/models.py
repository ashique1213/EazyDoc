from decimal import Decimal
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class ClinicStatus(models.TextChoices):
    """
    Clinic lifecycle and verification statuses.
    Transitions:
      DRAFT -> PENDING (Owner submits)
      PENDING -> APPROVED (Admin approves)
      PENDING -> REJECTED (Admin rejects with reason)
      REJECTED -> PENDING (Owner resubmits after correction)
      APPROVED -> SUSPENDED (Admin suspends with reason)
      SUSPENDED -> APPROVED (Admin reactivates)
    """
    DRAFT = "DRAFT", _("Draft")
    PENDING = "PENDING", _("Pending Verification")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    SUSPENDED = "SUSPENDED", _("Suspended")


class Clinic(models.Model):
    """
    Core healthcare establishment entity representing a clinic/hospital facility.
    Each clinic is owned by a CLINIC_OWNER user and undergoes Super Admin verification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("clinic name"), max_length=255, db_index=True)
    slug = models.SlugField(_("slug"), max_length=255, unique=True, db_index=True)
    description = models.TextField(_("description"), blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="owned_clinics",
        verbose_name=_("clinic owner"),
        db_index=True,
    )
    email = models.EmailField(_("official email"), max_length=255)
    phone = models.CharField(_("official phone"), max_length=20)
    address_line_1 = models.CharField(_("address line 1"), max_length=255)
    address_line_2 = models.CharField(
        _("address line 2"), max_length=255, blank=True, null=True, default=""
    )
    city = models.CharField(_("city"), max_length=100, db_index=True)
    state = models.CharField(_("state"), max_length=100)
    pincode = models.CharField(_("postal / pin code"), max_length=20)
    country = models.CharField(_("country"), max_length=100, default="India")
    logo = models.ImageField(
        _("clinic logo"), upload_to="clinic_logos/", blank=True, null=True
    )
    status = models.CharField(
        _("verification status"),
        max_length=20,
        choices=ClinicStatus.choices,
        default=ClinicStatus.PENDING,
        db_index=True,
    )
    verification_notes = models.TextField(
        _("verification / rejection notes"), blank=True, null=True, default=""
    )
    timezone = models.CharField(
        _("operating timezone"), max_length=50, default="Asia/Kolkata"
    )
    is_verified = models.BooleanField(
        _("is verified"), default=False, db_index=True
    )
    created_at = models.DateTimeField(
        _("created at"), auto_now_add=True, db_index=True
    )
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    approved_at = models.DateTimeField(
        _("approved at"), null=True, blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_clinics",
        verbose_name=_("approved by"),
    )

    class Meta:
        verbose_name = _("clinic")
        verbose_name_plural = _("clinics")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["city", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    @property
    def phone_number(self) -> str:
        """Alias for compatibility with legacy specifications."""
        return self.phone

    @property
    def postal_code(self) -> str:
        """Alias for compatibility with legacy specifications."""
        return self.pincode

    @property
    def is_publicly_bookable(self) -> bool:
        """Only APPROVED clinics can accept appointments and appear in public discovery."""
        return self.status == ClinicStatus.APPROVED

    def generate_unique_slug(self) -> str:
        """Generates a human-readable unique slug from the clinic name, handling collisions."""
        base_slug = slugify(self.name) or f"clinic-{uuid.uuid4().hex[:8]}"
        slug = base_slug
        counter = 1
        qs = Clinic.objects.exclude(pk=self.pk) if self.pk else Clinic.objects.all()

        while qs.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        # Ensure is_verified stays aligned with status
        self.is_verified = self.status == ClinicStatus.APPROVED
        super().save(*args, **kwargs)


class DoctorClinicStatus(models.TextChoices):
    """
    Lifecycle statuses for doctor-clinic affiliation.
    Transitions:
      INVITED -> ACTIVE (Doctor accepts invitation)
      INVITED -> REJECTED (Doctor rejects invitation)
      ACTIVE -> REMOVED (Clinic owner ends active association)
      ACTIVE -> SUSPENDED (Administrator suspends association)
      REJECTED / REMOVED -> INVITED (Clinic owner re-invites doctor)
      SUSPENDED -> ACTIVE (Administrator reactivates association)
    """
    INVITED = "INVITED", _("Invited")
    ACTIVE = "ACTIVE", _("Active")
    REJECTED = "REJECTED", _("Rejected")
    REMOVED = "REMOVED", _("Removed")
    SUSPENDED = "SUSPENDED", _("Suspended")


class DoctorClinic(models.Model):
    """
    Associative relationship linking a reusable global Doctor profile to a Clinic.
    Stores clinic-specific commercial terms (consultation fees, duration) independently per clinic.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="clinic_associations",
        verbose_name=_("doctor profile"),
        db_index=True,
    )
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="doctor_associations",
        verbose_name=_("clinic"),
        db_index=True,
    )
    status = models.CharField(
        _("association status"),
        max_length=20,
        choices=DoctorClinicStatus.choices,
        default=DoctorClinicStatus.INVITED,
        db_index=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_doctor_invitations",
        verbose_name=_("invited by"),
        help_text=_("User who initiated the invitation."),
    )
    invitation_message = models.TextField(
        _("invitation message"),
        blank=True,
        default="",
        help_text=_("Optional welcome note or affiliation terms."),
    )
    consultation_fee = models.DecimalField(
        _("consultation fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Clinic-specific consultation fee in INR."),
    )
    follow_up_fee = models.DecimalField(
        _("follow-up consultation fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Optional clinic-specific follow-up consultation fee in INR."),
    )
    appointment_duration_minutes = models.PositiveIntegerField(
        _("appointment duration (minutes)"),
        default=15,
        help_text=_("Standard appointment slot duration in minutes (between 5 and 240 minutes)."),
    )
    accepted_at = models.DateTimeField(
        _("accepted at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the doctor accepted the invitation."),
    )
    rejected_at = models.DateTimeField(
        _("rejected at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the doctor rejected the invitation."),
    )
    removed_at = models.DateTimeField(
        _("removed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the clinic owner ended the active association."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "doctor_clinics_doctorclinic"
        verbose_name = _("doctor clinic association")
        verbose_name_plural = _("doctor clinic associations")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "clinic"],
                name="unique_doctor_clinic_association",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=DoctorClinicStatus.values),
                name="valid_doctor_clinic_status",
            ),
            models.CheckConstraint(
                condition=models.Q(consultation_fee__gte=0),
                name="valid_doctor_clinic_consultation_fee",
            ),
            models.CheckConstraint(
                condition=models.Q(follow_up_fee__gte=0),
                name="valid_doctor_clinic_follow_up_fee",
            ),
            models.CheckConstraint(
                condition=models.Q(appointment_duration_minutes__gte=5, appointment_duration_minutes__lte=240),
                name="valid_doctor_clinic_duration",
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "status"]),
            models.Index(fields=["doctor", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.doctor.full_name} @ {self.clinic.name} ({self.status})"

    def clean(self):
        super().clean()
        if self.consultation_fee is not None and self.consultation_fee < Decimal("0.00"):
            raise ValidationError({"consultation_fee": _("Consultation fee cannot be negative.")})
        if self.follow_up_fee is not None and self.follow_up_fee < Decimal("0.00"):
            raise ValidationError({"follow_up_fee": _("Follow-up fee cannot be negative.")})
        if self.appointment_duration_minutes is not None:
            if self.appointment_duration_minutes < 5 or self.appointment_duration_minutes > 240:
                raise ValidationError({"appointment_duration_minutes": _("Duration must be between 5 and 240 minutes.")})
