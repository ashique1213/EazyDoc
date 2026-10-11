import os
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image

MAX_PHOTO_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Registration number: typically alphanumeric with optional hyphens, slashes, dots
REG_NUMBER_REGEX = re.compile(r"^[A-Za-z0-9\-\/\.]{3,50}$")


def normalize_registration_number(value: str) -> str:
    """
    Normalizes medical registration number by removing all whitespace
    and converting to uppercase.
    Example: ' MMC / 12345 ' -> 'MMC/12345'
    """
    if not value:
        return ""
    return re.sub(r"\s+", "", str(value)).upper()


def normalize_council_name(value: str) -> str:
    """
    Normalizes medical registration council name by collapsing whitespace
    and converting to uppercase.
    Example: ' Maharashtra  Medical  Council ' -> 'MAHARASHTRA MEDICAL COUNCIL'
    """
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().upper()


def validate_registration_number(value: str) -> None:
    """
    Validates registration number format.
    Must be between 3 and 50 characters, containing only letters, numbers, hyphens, slashes, or dots.
    """
    if not value or not str(value).strip():
        raise ValidationError(_("Registration number is required."))
    cleaned = str(value).strip()
    if len(cleaned) < 3 or len(cleaned) > 50:
        raise ValidationError(_("Registration number must be between 3 and 50 characters."))
    # Check normalized representation
    normalized = normalize_registration_number(cleaned)
    if not REG_NUMBER_REGEX.match(normalized):
        raise ValidationError(
            _("Registration number may only contain letters, numbers, hyphens, slashes, and periods.")
        )


def validate_registration_council(value: str) -> None:
    """
    Validates registration council name.
    """
    if not value or not str(value).strip():
        raise ValidationError(_("Registration council / authority is required."))
    cleaned = str(value).strip()
    if len(cleaned) < 3 or len(cleaned) > 200:
        raise ValidationError(_("Registration council name must be between 3 and 200 characters."))


def validate_doctor_photo(file) -> None:
    """
    Validates uploaded doctor profile photo:
    1. Maximum file size (2MB)
    2. Allowed file extension (.jpg, .jpeg, .png, .webp)
    3. Content type header
    4. Genuine image inspection using Pillow
    """
    if not file:
        return

    if file.size > MAX_PHOTO_SIZE_BYTES:
        raise ValidationError(
            _(f"Profile photo exceeds the 2MB limit (current: {file.size / (1024 * 1024):.2f}MB).")
        )

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValidationError(
            _(f"Unsupported file format '{ext}'. Allowed formats: JPG, PNG, WebP.")
        )

    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise ValidationError(
            _(f"Invalid image MIME type '{content_type}'. Must be image/jpeg, image/png, or image/webp.")
        )

    try:
        file.seek(0)
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except Exception as exc:
        raise ValidationError(_("Uploaded file is corrupted or not a valid image.")) from exc


def validate_doctor_document(file) -> None:
    """
    Validates uploaded doctor verification document:
    1. Maximum file size (5MB)
    2. Allowed file extension (.pdf, .jpg, .jpeg, .png, .webp)
    3. Genuine file format check
    """
    if not file:
        raise ValidationError(_("Document file is required."))

    if file.size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError(
            _(f"Document file size exceeds the 5MB limit (current: {file.size / (1024 * 1024):.2f}MB).")
        )

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            _(f"Unsupported document format '{ext}'. Allowed formats: PDF, JPG, PNG, WebP.")
        )

    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise ValidationError(
            _(f"Invalid file MIME type '{content_type}'. Must be PDF or image.")
        )

    # If it is an image extension, verify with Pillow
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            file.seek(0)
            img = Image.open(file)
            img.verify()
            file.seek(0)
        except Exception as exc:
            raise ValidationError(_("Uploaded file is corrupted or not a valid image.")) from exc
