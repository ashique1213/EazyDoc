import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .validators import (
    normalize_council_name,
    normalize_registration_number,
    validate_doctor_photo,
    validate_registration_council,
    validate_registration_number,
)


class DoctorVerificationStatus(models.TextChoices):
    """
    Doctor lifecycle and medical registration verification statuses.
    Transitions:
      DRAFT -> PENDING (Doctor submits completed profile)
      PENDING -> VERIFIED (Super Admin verifies)
      PENDING -> REJECTED (Super Admin rejects with reason)
      REJECTED -> PENDING (Doctor resubmits after correction)
      VERIFIED -> SUSPENDED (Super Admin suspends with reason)
      SUSPENDED -> VERIFIED (Super Admin reactivates)
    """
    DRAFT = "DRAFT", _("Draft")
    PENDING = "PENDING", _("Pending Verification")
    VERIFIED = "VERIFIED", _("Verified")
    REJECTED = "REJECTED", _("Rejected")
    SUSPENDED = "SUSPENDED", _("Suspended")


class DoctorDocumentType(models.TextChoices):
    """Standardized medical verification document categories."""
    REGISTRATION_CERTIFICATE = "REGISTRATION_CERTIFICATE", _("Medical Registration Certificate")
    DEGREE_CERTIFICATE = "DEGREE_CERTIFICATE", _("Medical Degree / Qualifications")
    GOVERNMENT_ID = "GOVERNMENT_ID", _("Government Identity Proof")
    OTHER = "OTHER", _("Other Supporting Document")


class Specialization(models.Model):
    """
    Controlled catalog of medical specialties (e.g., Cardiology, Dermatology).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("specialization name"), max_length=100, unique=True, db_index=True)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("specialization")
        verbose_name_plural = _("specializations")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Doctor(models.Model):
    """
    Global practitioner profile representing a licensed doctor.
    A doctor maintains a single global medical identity linked to their User account,
    which can subsequently be affiliated with multiple clinics across the platform.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        verbose_name=_("user account"),
    )
    registration_number = models.CharField(
        _("registration number"),
        max_length=100,
        db_index=True,
        help_text=_("Official medical council registration number (e.g. MMC-12345)."),
    )
    normalized_registration_number = models.CharField(
        _("normalized registration number"),
        max_length=100,
        db_index=True,
        help_text=_("Normalized registration identifier (whitespace-stripped and uppercase) for collision prevention."),
    )
    registration_council = models.CharField(
        _("registration council"),
        max_length=200,
        db_index=True,
        help_text=_("Issuing Medical Council or Authority (e.g. Maharashtra Medical Council)."),
    )
    normalized_registration_council = models.CharField(
        _("normalized registration council"),
        max_length=200,
        db_index=True,
        help_text=_("Normalized issuing council name for multi-council uniqueness checking."),
    )
    registration_state = models.CharField(
        _("registration state / jurisdiction"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("State or jurisdiction where the registration was issued."),
    )
    full_name = models.CharField(_("full name"), max_length=200)
    specialization = models.CharField(
        _("specialization"),
        max_length=150,
        db_index=True,
        help_text=_("Primary medical specialization (e.g. Cardiology, General Medicine)."),
    )
    qualifications = models.CharField(
        _("qualifications"),
        max_length=255,
        help_text=_("Degrees and medical credentials (e.g. MBBS, MD, MS, DNB)."),
    )
    years_of_experience = models.PositiveIntegerField(
        _("years of experience"),
        default=0,
        help_text=_("Number of completed years of clinical experience."),
    )
    bio = models.TextField(
        _("biography"),
        blank=True,
        default="",
        help_text=_("Clinical background and area of expertise."),
    )
    languages = models.CharField(
        _("languages spoken"),
        max_length=255,
        blank=True,
        default="English",
        help_text=_("Comma-separated languages spoken with patients (e.g. English, Hindi)."),
    )
    profile_photo = models.ImageField(
        _("profile photo"),
        upload_to="doctor_photos/",
        blank=True,
        null=True,
        validators=[validate_doctor_photo],
    )
    verification_status = models.CharField(
        _("verification status"),
        max_length=20,
        choices=DoctorVerificationStatus.choices,
        default=DoctorVerificationStatus.DRAFT,
        db_index=True,
    )
    is_verified = models.BooleanField(
        _("is verified"),
        default=False,
        db_index=True,
        help_text=_("True strictly when verification status is VERIFIED."),
    )
    verification_notes = models.TextField(
        _("verification notes"),
        blank=True,
        default="",
        help_text=_("Administrative review notes or rejection reason required for resubmission."),
    )
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the doctor submitted their profile for admin verification."),
    )
    verified_at = models.DateTimeField(
        _("verified / reviewed at"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the Super Admin reviewed the profile."),
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_doctors",
        verbose_name=_("verified by"),
        help_text=_("Super Administrator who performed the verification decision."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("doctor")
        verbose_name_plural = _("doctors")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_registration_council", "normalized_registration_number"],
                name="unique_doctor_council_normalized_reg_no",
            ),
            models.CheckConstraint(
                condition=models.Q(verification_status__in=DoctorVerificationStatus.values),
                name="valid_doctor_verification_status",
            ),
            models.CheckConstraint(
                condition=models.Q(years_of_experience__gte=0),
                name="valid_doctor_experience_years",
            ),
        ]
        indexes = [
            models.Index(fields=["verification_status", "created_at"]),
            models.Index(fields=["specialization", "verification_status"]),
            models.Index(fields=["normalized_registration_council", "normalized_registration_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.registration_number}) - {self.verification_status}"

    @property
    def is_eligible_for_clinics(self) -> bool:
        """Only VERIFIED doctors whose account is active can associate with clinics."""
        return self.verification_status == DoctorVerificationStatus.VERIFIED and bool(self.user and self.user.is_active)

    def clean(self):
        super().clean()
        if self.registration_number:
            validate_registration_number(self.registration_number)
            self.normalized_registration_number = normalize_registration_number(self.registration_number)
        if self.registration_council:
            validate_registration_council(self.registration_council)
            self.normalized_registration_council = normalize_council_name(self.registration_council)

        # Enforce uniqueness across doctors in clean() for early application-level validation
        if self.normalized_registration_council and self.normalized_registration_number:
            qs = Doctor.objects.filter(
                normalized_registration_council=self.normalized_registration_council,
                normalized_registration_number=self.normalized_registration_number,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    "registration_number": _(
                        "A doctor profile with this medical registration number and council already exists."
                    )
                })

    def save(self, *args, **kwargs):
        if self.registration_number:
            self.normalized_registration_number = normalize_registration_number(self.registration_number)
        if self.registration_council:
            self.normalized_registration_council = normalize_council_name(self.registration_council)
        # Keep is_verified aligned with verification_status
        self.is_verified = (self.verification_status == DoctorVerificationStatus.VERIFIED)
        super().save(*args, **kwargs)


class DoctorDocument(models.Model):
    """
    Secure medical registration evidence uploaded by a doctor for Super Admin review.
    Stored privately and restricted to the doctor and authorized Super Administrators.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("doctor profile"),
    )
    document_type = models.CharField(
        _("document type"),
        max_length=50,
        choices=DoctorDocumentType.choices,
        default=DoctorDocumentType.REGISTRATION_CERTIFICATE,
    )
    file = models.FileField(
        _("document file"),
        upload_to="doctor_documents/private/",
    )
    file_name = models.CharField(_("original file name"), max_length=255)
    file_size = models.PositiveIntegerField(_("file size in bytes"), help_text=_("Size of document in bytes."))
    mime_type = models.CharField(_("mime type"), max_length=100, blank=True, default="")
    uploaded_at = models.DateTimeField(_("uploaded at"), auto_now_add=True)

    class Meta:
        verbose_name = _("doctor document")
        verbose_name_plural = _("doctor documents")
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.doctor.full_name} - {self.get_document_type_display()} ({self.file_name})"
