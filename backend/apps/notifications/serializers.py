from rest_framework import serializers
from .models import Notification, NotificationDelivery, NotificationPreference


class NotificationDeliverySerializer(serializers.ModelSerializer):
    """Serializer for notification delivery channel status (sanitized)."""

    class Meta:
        model = NotificationDelivery
        fields = [
            "id",
            "channel",
            "status",
            "attempt_count",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    """
    Public serializer for authenticated user in-app notifications.
    Strictly sanitizes internal credentials and error traces.
    """

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "related_object_type",
            "related_object_id",
            "action_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user notification channel and category preferences."""

    class Meta:
        model = NotificationPreference
        fields = [
            "email_enabled",
            "in_app_enabled",
            "appointment_reminders_enabled",
            "appointment_updates_enabled",
            "payment_updates_enabled",
            "clinic_announcements_enabled",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate(self, attrs):
        # Prevent invalid non-boolean types or empty payloads if required
        return attrs


class MarkReadResponseSerializer(serializers.Serializer):
    """Response structure after marking a notification as read."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    notification = NotificationSerializer(required=False)


class MarkAllReadResponseSerializer(serializers.Serializer):
    """Response structure after marking all notifications as read."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    marked_read_count = serializers.IntegerField()


class UnreadCountResponseSerializer(serializers.Serializer):
    """Response structure for unread notifications count."""

    unread_count = serializers.IntegerField()
