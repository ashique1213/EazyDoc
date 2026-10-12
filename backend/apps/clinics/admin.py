from django.contrib import admin
from .models import Clinic, DoctorClinic


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "owner",
        "city",
        "state",
        "status",
        "is_verified",
        "created_at",
    )
    list_filter = ("status", "is_verified", "city", "country")
    search_fields = ("name", "slug", "email", "phone", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "approved_at", "approved_by")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DoctorClinic)
class DoctorClinicAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "clinic",
        "status",
        "consultation_fee",
        "appointment_duration_minutes",
        "accepted_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "doctor__full_name",
        "doctor__registration_number",
        "clinic__name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "accepted_at", "rejected_at", "removed_at")
