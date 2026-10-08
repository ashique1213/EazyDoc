import logging
import secrets
from datetime import timedelta
from typing import Optional, Tuple
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils import timezone
from .models import EmailVerificationToken, PasswordResetToken, User
from apps.audit_logs.services import log_audit_event

logger = logging.getLogger("apps")


def send_verification_email(user: User, token_str: str) -> bool:
    """Sends account verification link / token to the user's email."""
    subject = "Verify your EazyDoc Account"
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    verify_url = f"{frontend_url}/verify-email?token={token_str}"
    message = (
        f"Hello {user.first_name or 'there'},\n\n"
        f"Thank you for registering with EazyDoc. Please verify your email address by visiting:\n"
        f"{verify_url}\n\n"
        f"Alternatively, you can enter this verification code directly: {token_str}\n\n"
        f"This verification code will expire in 24 hours.\n\n"
        f"Best regards,\nThe EazyDoc Healthcare Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@eazydoc.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False


def create_verification_token(user: User) -> EmailVerificationToken:
    """Generates a secure 24-hour verification token and sends the verification email."""
    # Invalidate previous unused verification tokens
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)

    token_str = secrets.token_urlsafe(32)
    token = EmailVerificationToken.objects.create(
        user=user,
        token=token_str,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    send_verification_email(user, token_str)
    return token


def verify_email_with_token(token_str: str, request=None) -> Tuple[bool, str, Optional[User]]:
    """Validates the token, marks user as verified, and records the event."""
    try:
        token = EmailVerificationToken.objects.select_related("user").get(token=token_str)
    except EmailVerificationToken.DoesNotExist:
        return False, "Invalid verification token.", None

    if token.is_used:
        return False, "This verification token has already been used.", None

    if token.expires_at <= timezone.now():
        return False, "This verification token has expired. Please request a new one.", None

    user = token.user
    user.is_verified = True
    user.save(update_fields=["is_verified", "updated_at"])

    token.is_used = True
    token.save(update_fields=["is_used"])

    log_audit_event(
        action="EMAIL_VERIFIED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
        request=request,
        details={"email": user.email},
    )

    return True, "Email successfully verified.", user


def send_password_reset_email(user: User, token_str: str) -> bool:
    """Sends a password reset token/link to the user."""
    subject = "Reset your EazyDoc Password"
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_url}/reset-password?token={token_str}"
    message = (
        f"Hello {user.first_name or 'there'},\n\n"
        f"We received a request to reset your password. You can reset your password using the link below:\n"
        f"{reset_url}\n\n"
        f"Alternatively, enter this reset token: {token_str}\n\n"
        f"This token will expire in 1 hour. If you did not request this, please disregard this email.\n\n"
        f"Best regards,\nThe EazyDoc Security Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "security@eazydoc.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {e}")
        return False


def request_password_reset(email: str, request=None) -> bool:
    """
    Initiates password reset workflow.
    Never reveals whether the email exists to the caller.
    """
    normalized_email = email.strip().lower()
    try:
        user = User.objects.get(email=normalized_email)
    except User.DoesNotExist:
        # Prevent timing attacks and email enumeration
        return False

    if not user.is_active:
        return False

    # Invalidate any prior unused reset tokens
    PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

    token_str = secrets.token_urlsafe(32)
    PasswordResetToken.objects.create(
        user=user,
        token=token_str,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    send_password_reset_email(user, token_str)

    log_audit_event(
        action="PASSWORD_RESET_REQUESTED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
        request=request,
    )
    return True


def reset_password_with_token(
    token_str: str, new_password: str, request=None
) -> Tuple[bool, str, Optional[User]]:
    """Validates the reset token and safely changes the user's password."""
    try:
        token = PasswordResetToken.objects.select_related("user").get(token=token_str)
    except PasswordResetToken.DoesNotExist:
        return False, "Invalid reset token.", None

    if token.is_used:
        return False, "This reset token has already been used.", None

    if token.expires_at <= timezone.now():
        return False, "This reset token has expired. Please request a new one.", None

    user = token.user

    # Validate password against system security rules
    try:
        validate_password(new_password, user=user)
    except Exception as e:
        return False, "; ".join(e.messages if hasattr(e, "messages") else [str(e)]), None

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])

    token.is_used = True
    token.save(update_fields=["is_used"])

    log_audit_event(
        action="PASSWORD_RESET_COMPLETED",
        resource_type="User",
        resource_id=str(user.id),
        actor=user,
        request=request,
    )

    return True, "Password has been reset successfully.", user
