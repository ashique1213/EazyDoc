from rest_framework import serializers
from .models import AuditLog


class AdminAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()
    actor_name = serializers.SerializerMethodField()
    actor_role = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_id",
            "actor_email",
            "actor_name",
            "actor_role",
            "clinic_id",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "user_agent",
            "details",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else "System"

    def get_actor_name(self, obj):
        if obj.actor:
            return f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.email
        return "System / Anonymous"

    def get_actor_role(self, obj):
        return getattr(obj.actor, "role", "SYSTEM") if obj.actor else "SYSTEM"
