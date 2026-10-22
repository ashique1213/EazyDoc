from django.contrib import admin
from .models import CommissionRecord, Payment, PaymentAuditLog, PaymentWebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "gateway_order_id", "patient", "clinic", "amount", "currency", "status", "paid_at", "created_at"]
    list_filter = ["status", "gateway_name", "currency", "created_at"]
    search_fields = ["gateway_order_id", "gateway_payment_id", "patient__email", "appointment__booking_reference"]
    readonly_fields = ["id", "gateway_order_id", "gateway_payment_id", "gateway_signature", "amount", "currency", "created_at", "updated_at", "paid_at"]

    def has_delete_permission(self, request, obj=None):
        return False  # Financial records are immutable audit trails


@admin.register(CommissionRecord)
class CommissionRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "clinic", "gross_amount", "commission_rate", "commission_amount", "clinic_share", "currency", "status", "created_at"]
    list_filter = ["status", "created_at", "clinic"]
    search_fields = ["clinic__name", "appointment__booking_reference", "payment__gateway_order_id"]
    readonly_fields = ["id", "payment", "appointment", "clinic", "gross_amount", "commission_rate", "commission_amount", "clinic_share", "created_at", "updated_at"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ["id", "event_id", "event_type", "gateway_name", "status", "received_at", "processed_at"]
    list_filter = ["status", "gateway_name", "event_type", "received_at"]
    search_fields = ["event_id", "event_type"]
    readonly_fields = ["id", "event_id", "event_type", "gateway_name", "status", "payload", "received_at", "processed_at", "error_message"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "event_type", "payment", "appointment", "actor", "created_at"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["payment__gateway_order_id", "appointment__booking_reference", "actor__email"]
    readonly_fields = ["id", "payment", "appointment", "event_type", "actor", "ip_address", "data", "created_at"]

    def has_delete_permission(self, request, obj=None):
        return False
