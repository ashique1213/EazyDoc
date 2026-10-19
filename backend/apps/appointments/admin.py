from django.contrib import admin
from .models import Appointment, AppointmentIdempotency


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference",
        "patient",
        "doctor",
        "clinic",
        "start_at",
        "status",
        "consultation_fee",
        "currency",
    )
    list_filter = ("status", "currency", "clinic", "created_at")
    search_fields = (
        "booking_reference",
        "patient__email",
        "doctor__full_name",
        "clinic__name",
    )
    readonly_fields = ("booking_reference", "created_at", "updated_at")


@admin.register(AppointmentIdempotency)
class AppointmentIdempotencyAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "patient", "appointment", "created_at")
    search_fields = ("idempotency_key", "patient__email")
    readonly_fields = ("created_at", "updated_at")
