from django.contrib import admin
from .models import Appointment, AppointmentHistory, AppointmentIdempotency


class AppointmentHistoryInline(admin.TabularInline):
    model = AppointmentHistory
    extra = 0
    readonly_fields = (
        "id",
        "event_type",
        "previous_status",
        "new_status",
        "previous_start_at",
        "previous_end_at",
        "new_start_at",
        "new_end_at",
        "actor",
        "actor_role",
        "reason",
        "is_exception",
        "created_at",
    )
    can_delete = False


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference",
        "patient",
        "doctor",
        "clinic",
        "start_at",
        "status",
        "reschedule_required",
        "consultation_fee",
        "currency",
    )
    list_filter = ("status", "reschedule_required", "currency", "clinic", "created_at")
    search_fields = (
        "booking_reference",
        "patient__email",
        "doctor__full_name",
        "clinic__name",
    )
    readonly_fields = ("booking_reference", "created_at", "updated_at", "cancelled_at")
    inlines = [AppointmentHistoryInline]


@admin.register(AppointmentHistory)
class AppointmentHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "appointment",
        "event_type",
        "previous_status",
        "new_status",
        "actor",
        "actor_role",
        "is_exception",
        "created_at",
    )
    list_filter = ("event_type", "is_exception", "created_at")
    search_fields = ("appointment__booking_reference", "reason", "actor__email")
    readonly_fields = [f.name for f in AppointmentHistory._meta.fields]


@admin.register(AppointmentIdempotency)
class AppointmentIdempotencyAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "patient", "appointment", "created_at")
    search_fields = ("idempotency_key", "patient__email")
    readonly_fields = ("created_at", "updated_at")

