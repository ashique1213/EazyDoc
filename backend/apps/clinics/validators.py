import os
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_LOGO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_LOGO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Standard phone: optional +, followed by 10 to 15 digits
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{9,14}$")

# Indian PIN code: 6 digits, first digit non-zero
INDIA_PINCODE_REGEX = re.compile(r"^[1-9]\d{5}$")
# General postal code: 3 to 10 alphanumeric characters, dashes, or spaces
GENERAL_PINCODE_REGEX = re.compile(r"^[A-Za-z0-9\s\-]{3,10}$")


def validate_clinic_logo(file):
    """
    Validates uploaded clinic logo:
    1. Maximum file size (2MB)
    2. Allowed file extension (.jpg, .jpeg, .png, .webp)
    3. Content type header
    4. Genuine image inspection using Pillow
    """
    if not file:
        return

    # Check size
    if file.size > MAX_LOGO_SIZE_BYTES:
        raise ValidationError(
            _(f"Logo file size exceeds the 2MB limit (current: {file.size / (1024 * 1024):.2f}MB).")
        )

    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise ValidationError(
            _(f"Unsupported file format '{ext}'. Allowed formats: JPG, PNG, WebP.")
        )

    # Check content_type if available on UploadedFile
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_LOGO_MIME_TYPES:
        raise ValidationError(
            _(f"Invalid image MIME type '{content_type}'. Must be image/jpeg, image/png, or image/webp.")
        )

    # Deep inspection with Pillow
    try:
        # Seek to start
        file.seek(0)
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except Exception as exc:
        raise ValidationError(_("Uploaded file is corrupted or not a valid image.")) from exc


def validate_clinic_phone(value: str) -> None:
    """Validates phone number format."""
    cleaned = value.strip().replace(" ", "").replace("-", "")
    if not PHONE_REGEX.match(cleaned):
        raise ValidationError(
            _("Enter a valid phone number with 10 to 15 digits (e.g., +919876543210 or 9876543210).")
        )


def validate_clinic_pincode(pincode: str, country: str = "India") -> None:
    """Validates postal code based on country."""
    cleaned = pincode.strip()
    if country and country.strip().lower() in ("india", "in"):
        if not INDIA_PINCODE_REGEX.match(cleaned):
            raise ValidationError(_("Enter a valid 6-digit Indian PIN code (e.g. 560001)."))
    else:
        if not GENERAL_PINCODE_REGEX.match(cleaned):
            raise ValidationError(_("Enter a valid postal / pin code."))
