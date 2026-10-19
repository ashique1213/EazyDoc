from datetime import datetime, time
from zoneinfo import ZoneInfo
from rest_framework import serializers
from django.utils import timezone

from apps.accounts.models import User
from apps.clinics.models import Clinic, DoctorClinic
from apps.doctors.models import Doctor
from .models import Appointment, AppointmentStatus


class AppointmentPatientSummarySerializer(serializers.ModelSerializer):
    """Safe public/summary view of the patient booking the consultation."""
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone"]
        read_only_fields = fields


class AppointmentDoctorSummarySerializer(serializers.ModelSerializer):
    """Doctor summary info included in appointment payloads."""
    class Meta:
        model = Doctor
        fields = ["id", "full_name", "specialization", "qualifications", "profile_photo"]
        read_only_fields = fields


class AppointmentClinicSummarySerializer(serializers.ModelSerializer):
    """Clinic summary info included in appointment payloads."""
    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "slug",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "phone",
            "email",
            "timezone",
        ]
        read_only_fields = fields


class AppointmentBookingRequestSerializer(serializers.Serializer):
    """
    Validates input parameters for creating a new patient appointment.
    Ensures trusted backend resolution of pricing, duration, and status.
    """
    clinic_id = serializers.UUIDField(required=True)
    doctor_id = serializers.UUIDField(required=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    date = serializers.DateField(required=False, allow_null=True)
    time = serializers.TimeField(required=False, allow_null=True)
    patient_note = serializers.CharField(
        required=False, allow_blank=True, max_length=1000, default=""
    )
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, max_length=128, default=""
    )

    def validate(self, attrs):
        start_at = attrs.get("start_at")
        req_date = attrs.get("date")
        req_time = attrs.get("time")

        if not start_at and not (req_date and req_time):
            raise serializers.ValidationError(
                "Either 'start_at' (ISO datetime) or both 'date' and 'time' must be provided."
            )

        # If date and time are provided without start_at, construct timezone-aware start_at using clinic's timezone
        if not start_at and req_date and req_time:
            clinic_id = attrs["clinic_id"]
            clinic = Clinic.objects.filter(id=clinic_id).first()
            tz_name = clinic.timezone if clinic else "Asia/Kolkata"
            try:
                clinic_tz = ZoneInfo(tz_name)
            except Exception:
                clinic_tz = ZoneInfo("Asia/Kolkata")

            combined_local = datetime.combine(req_date, req_time, tzinfo=clinic_tz)
            attrs["start_at"] = combined_local

        # Ensure start_at is timezone aware
        if not timezone.is_aware(attrs["start_at"]):
            raise serializers.ValidationError("Provided appointment start timestamp must be timezone-aware.")

        return attrs


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive representation of an appointment for authorized patient, clinic, or doctor.
    Never exposes internal commissions or unrelated private data.
    """
    doctor = AppointmentDoctorSummarySerializer(read_only=True)
    clinic = AppointmentClinicSummarySerializer(read_only=True)
    patient = AppointmentPatientSummarySerializer(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "booking_reference",
            "status",
            "start_at",
            "end_at",
            "duration_minutes",
            "consultation_fee",
            "currency",
            "patient_note",
            "doctor",
            "clinic",
            "patient",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AppointmentListSerializer(serializers.ModelSerializer):
    """
    Compact list representation for patient history and management dashboards.
    """
    doctor_name = serializers.CharField(source="doctor.full_name", read_only=True)
    specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    clinic_city = serializers.CharField(source="clinic.city", read_only=True)
    clinic_timezone = serializers.CharField(source="clinic.timezone", read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "booking_reference",
            "status",
            "start_at",
            "end_at",
            "duration_minutes",
            "consultation_fee",
            "currency",
            "patient_note",
            "doctor_id",
            "doctor_name",
            "specialization",
            "clinic_id",
            "clinic_name",
            "clinic_city",
            "clinic_timezone",
            "created_at",
        ]
        read_only_fields = fields
