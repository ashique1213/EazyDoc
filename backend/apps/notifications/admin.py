from django.contrib import admin
from .models import (
    AppointmentReminderSchedule,
    Notification,
    NotificationDelivery,
    NotificationPreference,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__email", "title", "message"]
    readonly_fields = ["id", "created_at", "read_at"]


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ["id", "notification", "channel", "status", "attempt_count", "sent_at", "created_at"]
    list_filter = ["channel", "status", "created_at"]
    search_fields = ["notification__recipient__email", "provider_message_id", "idempotency_key"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "email_enabled",
        "in_app_enabled",
        "appointment_reminders_enabled",
        "appointment_updates_enabled",
        "payment_updates_enabled",
    ]
    search_fields = ["user__email"]


@admin.register(AppointmentReminderSchedule)
class AppointmentReminderScheduleAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "appointment",
        "reminder_type",
        "scheduled_for",
        "schedule_version",
        "status",
        "sent_at",
    ]
    list_filter = ["reminder_type", "status", "schedule_version"]
    search_fields = ["appointment__booking_reference", "appointment__patient__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
