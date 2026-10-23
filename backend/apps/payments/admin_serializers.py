from decimal import Decimal
from rest_framework import serializers
from .models import CommissionRecord, Payment, PlatformSetting
from apps.clinics.models import Clinic


class AdminPaymentClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id", "name", "slug", "city"]


class AdminPaymentCommissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionRecord
        fields = [
            "id",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "clinic_share",
            "currency",
            "status",
            "settled_at",
            "created_at",
        ]


class AdminPaymentSerializer(serializers.ModelSerializer):
    clinic = AdminPaymentClinicSerializer(read_only=True)
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    patient_name = serializers.SerializerMethodField()
    booking_reference = serializers.CharField(source="appointment.booking_reference", read_only=True)
    appointment_status = serializers.CharField(source="appointment.status", read_only=True)
    commission_record = AdminPaymentCommissionRecordSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_name",
            "amount",
            "currency",
            "status",
            "failure_code",
            "failure_description",
            "paid_at",
            "created_at",
            "clinic",
            "patient_email",
            "patient_name",
            "booking_reference",
            "appointment_status",
            "commission_record",
        ]

    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}".strip() or obj.patient.email
        return ""


class AdminCommissionRecordSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source="appointment.booking_reference", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    clinic_slug = serializers.CharField(source="clinic.slug", read_only=True)
    gateway_order_id = serializers.CharField(source="payment.gateway_order_id", read_only=True)
    gateway_payment_id = serializers.CharField(source="payment.gateway_payment_id", read_only=True)

    class Meta:
        model = CommissionRecord
        fields = [
            "id",
            "payment_id",
            "appointment_id",
            "booking_reference",
            "clinic_id",
            "clinic_name",
            "clinic_slug",
            "gateway_order_id",
            "gateway_payment_id",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "clinic_share",
            "currency",
            "status",
            "settled_at",
            "created_at",
        ]


class AdminCommissionSettingsUpdateSerializer(serializers.Serializer):
    default_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
    )
    clinic_id = serializers.UUIDField(required=False, allow_null=True)
    clinic_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
    )
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
