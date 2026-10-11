from django.contrib import admin
from .models import Clinic


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
