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
