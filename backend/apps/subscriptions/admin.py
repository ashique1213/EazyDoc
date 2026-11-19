from django.contrib import admin
from apps.subscriptions.models import (
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPlan,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "tier", "billing_interval", "price", "max_doctors", "max_staff", "is_active", "sort_order"]
    list_filter = ["tier", "billing_interval", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["sort_order", "price"]


@admin.register(ClinicSubscription)
class ClinicSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["clinic", "plan", "status", "billing_interval", "current_period_end", "trial_end", "cancel_at_period_end"]
    list_filter = ["status", "billing_interval", "cancel_at_period_end", "plan__tier"]
    search_fields = ["clinic__name", "clinic__owner__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ["razorpay_order_id", "clinic", "plan", "amount", "currency", "status", "paid_at", "created_at"]
    list_filter = ["status", "currency", "billing_interval"]
    search_fields = ["razorpay_order_id", "razorpay_payment_id", "clinic__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "clinic", "plan_name", "subtotal_amount", "tax_amount", "total_amount", "status", "paid_at", "created_at"]
    list_filter = ["status", "tax_rate"]
    search_fields = ["invoice_number", "clinic__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "clinic", "event_type", "old_status", "new_status", "old_plan_name", "new_plan_name", "triggered_by"]
    list_filter = ["event_type", "new_status"]
    search_fields = ["clinic__name", "reason"]
    readonly_fields = ["created_at"]
