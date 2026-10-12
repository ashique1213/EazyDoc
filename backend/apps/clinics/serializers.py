from decimal import Decimal
from rest_framework import serializers
from apps.accounts.models import User
from .models import Clinic, ClinicStatus
from .validators import (
    validate_clinic_logo,
    validate_clinic_phone,
    validate_clinic_pincode,
)


class ClinicOwnerSummarySerializer(serializers.ModelSerializer):
    """Compact summary of clinic owner or approver user account."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = fields


class ClinicSerializer(serializers.ModelSerializer):
    """Comprehensive read serializer for Clinic model."""

    owner = ClinicOwnerSummarySerializer(read_only=True)
    approved_by = ClinicOwnerSummarySerializer(read_only=True)
    is_publicly_bookable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "owner",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
            "status",
            "verification_notes",
            "timezone",
            "is_verified",
            "is_publicly_bookable",
            "created_at",
            "updated_at",
            "approved_at",
            "approved_by",
        ]
        read_only_fields = fields


class ClinicCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new clinic by an authenticated clinic owner.
    Enforces required field validation, phone/pincode formatting, and logo integrity.
    """

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_clinic_logo],
    )
    status = serializers.ChoiceField(
        choices=[(ClinicStatus.DRAFT, "Draft"), (ClinicStatus.PENDING, "Pending")],
        default=ClinicStatus.PENDING,
        required=False,
    )

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Clinic name is required.")
        return name

    def validate_phone(self, value: str) -> str:
        validate_clinic_phone(value)
        return value.strip()

    def validate(self, attrs):
        country = attrs.get("country", "India")
        pincode = attrs.get("pincode")
        if pincode:
            validate_clinic_pincode(pincode, country)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        # Clinic owner is always locked to the authenticated user
        validated_data["owner"] = user
        return super().create(validated_data)


class ClinicUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating clinic profile fields by the owner.
    Protects status, owner, verification notes, and approval metadata from tampering.
    """

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_clinic_logo],
    )

    class Meta:
        model = Clinic
        fields = [
            "name",
            "description",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Clinic name cannot be blank.")
        return name

    def validate_phone(self, value: str) -> str:
        validate_clinic_phone(value)
        return value.strip()

    def validate(self, attrs):
        country = attrs.get("country", getattr(self.instance, "country", "India"))
        pincode = attrs.get("pincode")
        if pincode:
            validate_clinic_pincode(pincode, country)
        return attrs


class ClinicAdminActionSerializer(serializers.Serializer):
    """Serializer for administrative actions requiring a mandatory reason (e.g., rejection, suspension)."""

    reason = serializers.CharField(
        required=True,
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
        error_messages={
            "required": "A reason is mandatory for this administrative action.",
            "blank": "Reason cannot be empty.",
            "min_length": "Please provide a detailed reason with at least 3 characters.",
        },
    )


class DoctorClinicDoctorSummarySerializer(serializers.ModelSerializer):
    """Safe, minimal doctor profile representation for clinic associations (no private documents or notes)."""

    profile_photo = serializers.ImageField(read_only=True)

    class Meta:
        from apps.doctors.models import Doctor

        model = Doctor
        fields = [
            "id",
            "full_name",
            "specialization",
            "qualifications",
            "years_of_experience",
            "registration_number",
            "registration_council",
            "profile_photo",
            "is_verified",
        ]
        read_only_fields = fields


class DoctorClinicClinicSummarySerializer(serializers.ModelSerializer):
    """Safe, minimal clinic representation for doctor's view of associations."""

    logo = serializers.ImageField(read_only=True)

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "country",
            "logo",
            "status",
        ]
        read_only_fields = fields


class DoctorClinicSerializer(serializers.ModelSerializer):
    """Comprehensive serialization of a DoctorClinic association."""

    doctor = DoctorClinicDoctorSummarySerializer(read_only=True)
    clinic = DoctorClinicClinicSummarySerializer(read_only=True)
    invited_by = ClinicOwnerSummarySerializer(read_only=True)

    class Meta:
        from .models import DoctorClinic

        model = DoctorClinic
        fields = [
            "id",
            "doctor",
            "clinic",
            "status",
            "invited_by",
            "invitation_message",
            "consultation_fee",
            "follow_up_fee",
            "appointment_duration_minutes",
            "accepted_at",
            "rejected_at",
            "removed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DoctorClinicInvitationCreateSerializer(serializers.Serializer):
    """Payload validation for inviting a doctor to a clinic."""

    doctor_id = serializers.UUIDField(required=True)
    invitation_message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=1000,
        trim_whitespace=True,
    )
    consultation_fee = serializers.DecimalField(
        required=False,
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    follow_up_fee = serializers.DecimalField(
        required=False,
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    appointment_duration_minutes = serializers.IntegerField(
        required=False,
        default=15,
        min_value=5,
        max_value=240,
    )


class DoctorClinicSettingsUpdateSerializer(serializers.Serializer):
    """Payload validation for updating doctor association settings at a clinic."""

    consultation_fee = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    follow_up_fee = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    appointment_duration_minutes = serializers.IntegerField(
        required=False,
        min_value=5,
        max_value=240,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one setting parameter must be provided for update.")
        return attrs
