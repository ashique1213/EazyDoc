from rest_framework import serializers
from apps.subscriptions.models import (
    BillingInterval,
    ClinicSubscription,
    SubscriptionEvent,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionTier,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Public and clinic-facing subscription plan representation."""
    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "code",
            "tier",
            "billing_interval",
            "price",
            "currency",
            "description",
            "max_doctors",
            "max_staff",
            "max_appointments_per_month",
            "features",
            "feature_flags",
            "trial_days",
            "is_active",
            "is_public",
            "sort_order",
            "is_free",
        ]
        read_only_fields = fields


class SubscriptionPlanAdminSerializer(serializers.ModelSerializer):
    """Super Admin plan management serializer for creating and modifying SaaS plans."""

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "code",
            "tier",
            "billing_interval",
            "price",
            "currency",
            "description",
            "max_doctors",
            "max_staff",
            "max_appointments_per_month",
            "features",
            "feature_flags",
            "trial_days",
            "is_active",
            "is_public",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """Payment transaction details for clinic SaaS billing."""
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id",
            "clinic_id",
            "plan_name",
            "amount",
            "currency",
            "status",
            "billing_interval",
            "razorpay_order_id",
            "razorpay_payment_id",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    """Immutable invoice representation with GST breakdown."""
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = [
            "id",
            "invoice_number",
            "clinic_id",
            "clinic_name",
            "plan_name",
            "subtotal_amount",
            "tax_rate",
            "tax_amount",
            "total_amount",
            "currency",
            "status",
            "billing_period_start",
            "billing_period_end",
            "line_items",
            "billing_details",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionEventSerializer(serializers.ModelSerializer):
    """Audit event log serializer for subscription lifecycle changes."""
    triggered_by_name = serializers.SerializerMethodField()
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)

    class Meta:
        model = SubscriptionEvent
        fields = [
            "id",
            "clinic_id",
            "event_type",
            "old_status",
            "new_status",
            "old_plan_name",
            "new_plan_name",
            "reason",
            "metadata",
            "triggered_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_triggered_by_name(self, obj) -> str:
        if obj.triggered_by:
            return obj.triggered_by.get_full_name() or obj.triggered_by.email
        return "System / Automation"


class ClinicSubscriptionSerializer(serializers.ModelSerializer):
    """Active subscription status and plan details for a clinic."""
    clinic_id = serializers.UUIDField(source="clinic.id", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)
    is_in_trial = serializers.BooleanField(read_only=True)
    is_usable = serializers.BooleanField(read_only=True)
    effective_max_doctors = serializers.IntegerField(read_only=True)
    effective_max_staff = serializers.IntegerField(read_only=True)
    days_remaining_in_trial = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClinicSubscription
        fields = [
            "id",
            "clinic_id",
            "clinic_name",
            "plan",
            "status",
            "billing_interval",
            "current_period_start",
            "current_period_end",
            "trial_start",
            "trial_end",
            "has_used_trial",
            "cancel_at_period_end",
            "cancelled_at",
            "cancellation_reason",
            "past_due_since",
            "grace_period_ends_at",
            "custom_doctor_limit",
            "custom_staff_limit",
            "is_in_trial",
            "is_usable",
            "effective_max_doctors",
            "effective_max_staff",
            "days_remaining_in_trial",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubscriptionCheckoutRequestSerializer(serializers.Serializer):
    """Validates parameters for initializing a plan checkout order."""
    plan_id = serializers.UUIDField(required=True)
    billing_interval = serializers.ChoiceField(
        choices=BillingInterval.choices,
        default=BillingInterval.MONTHLY,
    )
    idempotency_key = serializers.CharField(max_length=128, required=False, allow_blank=True)


class SubscriptionVerifyPaymentRequestSerializer(serializers.Serializer):
    """Validates Razorpay Checkout signature verification payload."""
    razorpay_order_id = serializers.CharField(max_length=100, required=True)
    razorpay_payment_id = serializers.CharField(max_length=100, required=True)
    razorpay_signature = serializers.CharField(max_length=255, required=True)


class SubscriptionCancelRequestSerializer(serializers.Serializer):
    """Validates subscription cancellation request."""
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AdminSubscriptionOverrideSerializer(serializers.Serializer):
    """Validates Super Admin subscription override actions."""
    status = serializers.ChoiceField(choices=SubscriptionStatus.choices, required=False)
    plan_id = serializers.UUIDField(required=False)
    custom_doctor_limit = serializers.IntegerField(required=False, allow_null=True)
    custom_staff_limit = serializers.IntegerField(required=False, allow_null=True)
    extend_days = serializers.IntegerField(required=False, min_value=1, max_value=365)
    reason = serializers.CharField(max_length=255, required=True)
