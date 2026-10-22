from decimal import Decimal
from rest_framework import serializers
from django.conf import settings
from .models import CommissionRecord, Payment, PaymentStatus
from .services import rupees_to_paise


class CreatePaymentOrderInputSerializer(serializers.Serializer):
    """Input payload for initiating a Razorpay payment order."""
    appointment_id = serializers.UUIDField(required=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128, default="")


class PaymentOrderOutputSerializer(serializers.Serializer):
    """Public checkout details returned to the frontend."""
    order_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_paise = serializers.IntegerField()
    currency = serializers.CharField()
    key_id = serializers.CharField()
    appointment_id = serializers.UUIDField()
    booking_reference = serializers.CharField()
    doctor_name = serializers.CharField()
    clinic_name = serializers.CharField()


class VerifyPaymentInputSerializer(serializers.Serializer):
    """Verification payload submitted after Razorpay Checkout succeeds in the browser."""
    razorpay_order_id = serializers.CharField(required=True, max_length=100)
    razorpay_payment_id = serializers.CharField(required=True, max_length=100)
    razorpay_signature = serializers.CharField(required=True, max_length=255)


class PatientPaymentStatusSerializer(serializers.ModelSerializer):
    """
    Patient-facing payment status representation.
    Strictly excludes internal platform commission, clinic share, and settlement information.
    """
    booking_reference = serializers.CharField(source="appointment.booking_reference", read_only=True)
    appointment_status = serializers.CharField(source="appointment.status", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "appointment_id",
            "booking_reference",
            "appointment_status",
            "amount",
            "currency",
            "status",
            "gateway_order_id",
            "gateway_payment_id",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields


class ClinicCommissionRecordSerializer(serializers.ModelSerializer):
    """
    Clinic-facing and administrative financial transaction serializer.
    Exposes commission breakdown only to authorized clinic owners and platform administrators.
    """
    booking_reference = serializers.CharField(source="appointment.booking_reference", read_only=True)
    doctor_name = serializers.CharField(source="appointment.doctor.full_name", read_only=True)

    class Meta:
        model = CommissionRecord
        fields = [
            "id",
            "payment_id",
            "appointment_id",
            "booking_reference",
            "doctor_name",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "clinic_share",
            "currency",
            "status",
            "created_at",
            "settled_at",
        ]
        read_only_fields = fields


class AdminClinicCommissionUpdateSerializer(serializers.Serializer):
    """Protected payload for super admins configuring clinic-specific commission rate."""
    commission_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
        required=True,
    )
