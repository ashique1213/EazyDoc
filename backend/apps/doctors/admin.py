from django.contrib import admin
from .models import Doctor, DoctorDocument, Specialization


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class DoctorDocumentInline(admin.TabularInline):
    model = DoctorDocument
    extra = 0
    readonly_fields = ["file_name", "file_size", "mime_type", "uploaded_at"]


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "registration_number",
        "registration_council",
        "specialization",
        "verification_status",
        "is_verified",
        "created_at",
    ]
    list_filter = ["verification_status", "is_verified", "specialization", "registration_council"]
    search_fields = [
        "full_name",
        "registration_number",
        "normalized_registration_number",
        "registration_council",
        "user__email",
    ]
    readonly_fields = [
        "normalized_registration_number",
        "normalized_registration_council",
        "is_verified",
        "submitted_at",
        "verified_at",
        "verified_by",
        "created_at",
        "updated_at",
    ]
    inlines = [DoctorDocumentInline]


@admin.register(DoctorDocument)
class DoctorDocumentAdmin(admin.ModelAdmin):
    list_display = ["doctor", "document_type", "file_name", "file_size", "uploaded_at"]
    list_filter = ["document_type", "uploaded_at"]
    search_fields = ["doctor__full_name", "file_name"]
