import uuid
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    """Centralized definition of system user roles."""
    SUPER_ADMIN = "SUPER_ADMIN", _("Super Admin")
    CLINIC_OWNER = "CLINIC_OWNER", _("Clinic Owner")
    STAFF = "STAFF", _("Clinic Staff")
    DOCTOR = "DOCTOR", _("Doctor")
    PATIENT = "PATIENT", _("Patient")


class UserStatus(models.TextChoices):
    """Account lifecycle and access status."""
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    SUSPENDED = "SUSPENDED", _("Suspended")


class UserManager(BaseUserManager):
    """Custom manager for EazyDoc User model using email as unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model for EazyDoc multi-tenant healthcare SaaS platform."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    phone = models.CharField(
        _("phone number"), max_length=20, unique=True, null=True, blank=True, db_index=True
    )
    first_name = models.CharField(_("first name"), max_length=100, blank=True)
    last_name = models.CharField(_("last name"), max_length=100, blank=True)
    role = models.CharField(
        _("user role"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.PATIENT,
        db_index=True,
    )
    status = models.CharField(
        _("account status"),
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
    )
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_verified = models.BooleanField(_("is verified"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=UserRole.values),
                name="valid_user_role",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=UserStatus.values),
                name="valid_user_status",
            ),
        ]

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    @property
    def phone_number(self):
        """Backward compatibility alias for phone."""
        return self.phone

    @phone_number.setter
    def phone_number(self, value):
        self.phone = value


class EmailVerificationToken(models.Model):
    """Time-limited, single-use token for email address verification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_verification_tokens"
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("email verification token")
        verbose_name_plural = _("email verification tokens")

    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"VerifyToken({self.user.email}, valid={self.is_valid()})"


class PasswordResetToken(models.Model):
    """Cryptographically secure, single-use token for password recovery."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("password reset token")
        verbose_name_plural = _("password reset tokens")

    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"PasswordResetToken({self.user.email}, valid={self.is_valid()})"
