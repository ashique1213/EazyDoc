from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User
from .models import (
    Doctor,
    DoctorDocument,
    DoctorDocumentType,
    DoctorVerificationStatus,
    Specialization,
)
from .validators import (
    normalize_council_name,
    normalize_registration_number,
    validate_doctor_document,
    validate_doctor_photo,
    validate_registration_council,
    validate_registration_number,
)


class DoctorUserSummarySerializer(serializers.ModelSerializer):
    """Compact summary of the doctor or admin user account."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = fields


class SpecializationSerializer(serializers.ModelSerializer):
    """Serializer for medical specialization catalog."""

    class Meta:
        model = Specialization
        fields = ["id", "name", "slug", "description", "created_at"]
        read_only_fields = fields


class DoctorDocumentSerializer(serializers.ModelSerializer):
    """Serializer for medical registration and credential documents."""

    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = DoctorDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "file_name",
            "file_size",
            "mime_type",
            "uploaded_at",
        ]
        read_only_fields = fields


class DoctorDocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for securely uploading a registration evidence document."""

    file = serializers.FileField(validators=[validate_doctor_document])
    document_type = serializers.ChoiceField(
        choices=DoctorDocumentType.choices,
        default=DoctorDocumentType.REGISTRATION_CERTIFICATE,
    )

    class Meta:
        model = DoctorDocument
        fields = ["document_type", "file"]

    def create(self, validated_data):
        file = validated_data["file"]
        doctor = self.context["doctor"]
        return DoctorDocument.objects.create(
            doctor=doctor,
            document_type=validated_data["document_type"],
            file=file,
            file_name=file.name,
            file_size=file.size,
            mime_type=getattr(file, "content_type", "") or "",
        )


class DoctorProfileSerializer(serializers.ModelSerializer):
    """Comprehensive read serializer for the authenticated Doctor."""

    user = DoctorUserSummarySerializer(read_only=True)
    verified_by = DoctorUserSummarySerializer(read_only=True)
    documents = DoctorDocumentSerializer(many=True, read_only=True)
    is_eligible_for_clinics = serializers.BooleanField(read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "user",
            "registration_number",
            "registration_council",
            "registration_state",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "bio",
            "languages",
            "profile_photo",
            "verification_status",
            "is_verified",
            "verification_notes",
            "is_eligible_for_clinics",
            "submitted_at",
            "verified_at",
            "verified_by",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DoctorProfileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an initial Doctor profile for the authenticated DOCTOR user.
    Enforces format validation, council & registration number uniqueness, and defaults status to DRAFT.
    """

    profile_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_doctor_photo],
    )
    years_of_experience = serializers.IntegerField(min_value=0, default=0, required=False)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "registration_number",
            "registration_council",
            "registration_state",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "bio",
            "languages",
            "profile_photo",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_registration_number(self, value: str) -> str:
        validate_registration_number(value)
        return value.strip()

    def validate_registration_council(self, value: str) -> str:
        validate_registration_council(value)
        return value.strip()

    def validate_full_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(_("Full name cannot be empty."))
        return cleaned

    def validate_specialization(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(_("Specialization cannot be empty."))
        return cleaned

    def validate_qualifications(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(_("Qualifications cannot be empty."))
        return cleaned

    def validate(self, attrs):
        user = self.context["request"].user

        # Ensure user does not already have a doctor profile
        if Doctor.objects.filter(user=user).exists():
            raise serializers.ValidationError(_("A doctor profile already exists for this account."))

        # Enforce unique medical registration identity across the specified council
        reg_number = attrs.get("registration_number")
        council = attrs.get("registration_council")
        norm_number = normalize_registration_number(reg_number)
        norm_council = normalize_council_name(council)

        if Doctor.objects.filter(
            normalized_registration_council=norm_council,
            normalized_registration_number=norm_number,
        ).exists():
            raise serializers.ValidationError({
                "registration_number": _(
                    "A doctor profile with this medical registration number and council already exists."
                )
            })

        # Default full_name to user's first and last name if not provided
        if not attrs.get("full_name"):
            user_full = f"{user.first_name} {user.last_name}".strip()
            attrs["full_name"] = user_full if user_full else "Dr. " + user.email.split("@")[0].title()

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        doctor = Doctor.objects.create(
            user=user,
            verification_status=DoctorVerificationStatus.DRAFT,
            **validated_data,
        )
        return doctor


class DoctorProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating permitted profile fields by the authenticated doctor.
    Protects verification_status, verified_by, verified_at, and submitted_at from tampering.
    """

    profile_photo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_doctor_photo],
    )
    years_of_experience = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = Doctor
        fields = [
            "registration_number",
            "registration_council",
            "registration_state",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "bio",
            "languages",
            "profile_photo",
        ]

    def validate_registration_number(self, value: str) -> str:
        if value:
            validate_registration_number(value)
            return value.strip()
        return value

    def validate_registration_council(self, value: str) -> str:
        if value:
            validate_registration_council(value)
            return value.strip()
        return value

    def validate(self, attrs):
        instance = self.instance
        reg_number = attrs.get("registration_number", instance.registration_number if instance else "")
        council = attrs.get("registration_council", instance.registration_council if instance else "")

        if reg_number and council:
            norm_number = normalize_registration_number(reg_number)
            norm_council = normalize_council_name(council)

            qs = Doctor.objects.filter(
                normalized_registration_council=norm_council,
                normalized_registration_number=norm_number,
            )
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "registration_number": _(
                        "A doctor profile with this medical registration number and council already exists."
                    )
                })

        return attrs

    def update(self, instance, validated_data):
        # If registration details changed on a previously VERIFIED profile,
        # reset status to PENDING for re-verification
        reg_changed = (
            ("registration_number" in validated_data and validated_data["registration_number"] != instance.registration_number)
            or ("registration_council" in validated_data and validated_data["registration_council"] != instance.registration_council)
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if reg_changed and instance.verification_status == DoctorVerificationStatus.VERIFIED:
            instance.verification_status = DoctorVerificationStatus.PENDING
            instance.is_verified = False
            instance.verification_notes = "Registration details were updated; pending re-verification."

        instance.save()
        return instance


class DoctorAdminActionSerializer(serializers.Serializer):
    """Serializer for administrative rejection or suspension actions requiring a clear reason."""

    reason = serializers.CharField(
        min_length=5,
        max_length=1000,
        required=True,
        help_text=_("Detailed reason for the rejection or suspension."),
    )

    def validate_reason(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError(_("Reason must be at least 5 characters."))
        return cleaned


class DoctorAdminDetailSerializer(serializers.ModelSerializer):
    """Full administrative view of a doctor profile with verification audit and uploaded documents."""

    user = DoctorUserSummarySerializer(read_only=True)
    verified_by = DoctorUserSummarySerializer(read_only=True)
    documents = DoctorDocumentSerializer(many=True, read_only=True)
    is_eligible_for_clinics = serializers.BooleanField(read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "user",
            "registration_number",
            "normalized_registration_number",
            "registration_council",
            "normalized_registration_council",
            "registration_state",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "bio",
            "languages",
            "profile_photo",
            "verification_status",
            "is_verified",
            "verification_notes",
            "is_eligible_for_clinics",
            "submitted_at",
            "verified_at",
            "verified_by",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DoctorRegistrationLookupSerializer(serializers.Serializer):
    """
    Privacy-preserving registration lookup response for Clinic Owners.
    Exposes only verification and eligibility indicators.
    Never exposes email, phone, documents, notes, or patient data.
    """

    found = serializers.BooleanField()
    doctor_id = serializers.UUIDField(allow_null=True)
    full_name = serializers.CharField(allow_null=True)
    specialization = serializers.CharField(allow_null=True)
    registration_council = serializers.CharField(allow_null=True)
    registration_number = serializers.CharField(allow_null=True)
    is_verified = serializers.BooleanField()
    is_eligible_for_invitation = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_null=True)
