from django.contrib import admin
from .models import BlockedSlot, DoctorSchedule, DoctorUnavailability


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor_name",
        "clinic_name",
        "day_of_week",
        "start_time",
        "end_time",
        "slot_duration_minutes",
        "buffer_minutes",
        "is_active",
        "created_at",
    )
    list_filter = ("day_of_week", "is_active", "doctor_clinic__clinic")
    search_fields = (
        "doctor_clinic__doctor__full_name",
        "doctor_clinic__clinic__name",
        "doctor_clinic__doctor__registration_number",
    )
    readonly_fields = ("created_at", "updated_at")

    def doctor_name(self, obj):
        return obj.doctor_clinic.doctor.full_name

    def clinic_name(self, obj):
        return obj.doctor_clinic.clinic.name


@admin.register(DoctorUnavailability)
class DoctorUnavailabilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor",
        "clinic",
        "reason",
        "start_datetime",
        "end_datetime",
        "created_at",
    )
    list_filter = ("reason", "clinic")
    search_fields = ("doctor__full_name", "clinic__name", "notes")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor_clinic",
        "date",
        "start_time",
        "end_time",
        "reason",
        "created_at",
    )
    list_filter = ("date", "doctor_clinic__clinic")
    search_fields = (
        "doctor_clinic__doctor__full_name",
        "doctor_clinic__clinic__name",
        "reason",
    )
    readonly_fields = ("created_at", "updated_at")
