from rest_framework import serializers
from .models import User, UserRole, UserStatus


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Sanitized user serializer for Super Admin oversight.
    Guarantees password hashes, tokens, and sensitive credentials are never exposed.
    """
    full_name = serializers.SerializerMethodField()
    doctor_profile_id = serializers.SerializerMethodField()
    owned_clinics_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "status",
            "is_active",
            "is_staff",
            "is_verified",
            "created_at",
            "updated_at",
            "last_login",
            "doctor_profile_id",
            "owned_clinics_count",
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email

    def get_doctor_profile_id(self, obj):
        if hasattr(obj, "doctor_profile") and obj.doctor_profile:
            return str(obj.doctor_profile.id)
        return None

    def get_owned_clinics_count(self, obj) -> int:
        if hasattr(obj, "owned_clinics"):
            return obj.owned_clinics.count()
        return 0


class AdminUserActionSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Reason or administrative justification for the account status update.",
    )
