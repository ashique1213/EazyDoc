import zoneinfo
from decimal import Decimal
from rest_framework import serializers
from apps.accounts.models import User, UserRole, UserStatus
from apps.clinics.models import Clinic, ClinicClosure, ClinicStaff, ClinicStaffPermission
from apps.clinics.validators import validate_clinic_logo, validate_clinic_phone, validate_clinic_pincode


class ClinicManagementUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for clinic owners / authorized staff to update permitted operational clinic information.
    Field-level validation strictly prevents modification of status, is_verified, commission_rate, and owner.
    """

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
        validators=[validate_clinic_logo],
    )
    timezone = serializers.CharField(required=False)

    class Meta:
        model = Clinic
        fields = [
            "id",
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
            "timezone",
            "status",
            "is_verified",
            "commission_rate",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "is_verified",
            "commission_rate",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Clinic name cannot be blank.")
        return name

    def validate_phone(self, value: str) -> str:
        validate_clinic_phone(value)
        return value.strip()

    def validate_timezone(self, value: str) -> str:
        val = value.strip()
        try:
            zoneinfo.ZoneInfo(val)
        except Exception:
            raise serializers.ValidationError(f"'{val}' is not a valid IANA timezone identifier.")
        return val

    def validate(self, attrs):
        country = attrs.get("country", getattr(self.instance, "country", "India"))
        pincode = attrs.get("pincode")
        if pincode:
            validate_clinic_pincode(pincode, country)
        return attrs


class ClinicStaffUserSummarySerializer(serializers.ModelSerializer):
    """Safe user summary representation for clinic staff list."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role", "status", "is_active"]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class ClinicStaffSerializer(serializers.ModelSerializer):
    """Read serializer for clinic staff members."""

    user = ClinicStaffUserSummarySerializer(read_only=True)
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)

    class Meta:
        model = ClinicStaff
        fields = [
            "id",
            "clinic_id",
            "clinic_name",
            "user",
            "role_title",
            "permissions",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClinicStaffCreateSerializer(serializers.Serializer):
    """
    Serializer for clinic owners inviting or creating a staff member.
    Enforces valid roles, prevents privilege escalation, and validates permissions.
    """

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    role_title = serializers.CharField(required=False, default="Clinic Staff", max_length=100)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=ClinicStaffPermission.values),
        required=False,
        default=list,
    )
    password = serializers.CharField(required=False, write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate_permissions(self, value: list) -> list:
        valid_perms = set(ClinicStaffPermission.values)
        invalid = [p for p in value if p not in valid_perms]
        if invalid:
            raise serializers.ValidationError(f"Invalid permissions: {invalid}")
        return list(set(value))


class ClinicStaffUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating staff permissions and active status."""

    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=ClinicStaffPermission.values),
        required=False,
    )

    class Meta:
        model = ClinicStaff
        fields = ["role_title", "permissions", "is_active"]

    def validate_permissions(self, value: list) -> list:
        valid_perms = set(ClinicStaffPermission.values)
        invalid = [p for p in value if p not in valid_perms]
        if invalid:
            raise serializers.ValidationError(f"Invalid permissions: {invalid}")
        return list(set(value))


class ClinicClosureSerializer(serializers.ModelSerializer):
    """Read serializer for operational clinic closures."""

    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ClinicClosure
        fields = [
            "id",
            "clinic_id",
            "start_date",
            "end_date",
            "reason",
            "notes",
            "is_active",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return "System"


class ClinicClosureCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an operational clinic closure with confirmation support."""

    confirmed = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = ClinicClosure
        fields = [
            "start_date",
            "end_date",
            "reason",
            "notes",
            "confirmed",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "Closure end date must be on or after start date."})
        return attrs
