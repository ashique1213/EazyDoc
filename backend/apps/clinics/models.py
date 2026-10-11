import uuid
from django.conf import settings
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
