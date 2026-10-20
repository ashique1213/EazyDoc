from datetime import datetime, time
from typing import Optional
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
    cancellation_cutoff = serializers.SerializerMethodField()
    is_cancellable = serializers.SerializerMethodField()
    is_reschedulable = serializers.SerializerMethodField()

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
            "cancellation_reason",
            "cancelled_at",
            "reschedule_required",
            "cancellation_cutoff",
            "is_cancellable",
            "is_reschedulable",
            "doctor",
            "clinic",
            "patient",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_cancellation_cutoff(self, obj: Appointment) -> Optional[str]:
        from .services import get_appointment_cancellation_cutoff
        try:
            cutoff = get_appointment_cancellation_cutoff(obj)
            return cutoff.isoformat()
        except Exception:
            return None

    def get_is_cancellable(self, obj: Appointment) -> bool:
        from .services import check_patient_cancellation_eligibility
        try:
            eligible, _, _ = check_patient_cancellation_eligibility(obj)
            return eligible
        except Exception:
            return False

    def get_is_reschedulable(self, obj: Appointment) -> bool:
        from .services import check_patient_rescheduling_eligibility
        try:
            eligible, _, _ = check_patient_rescheduling_eligibility(obj)
            return eligible
        except Exception:
            return False


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
    cancellation_cutoff = serializers.SerializerMethodField()
    is_cancellable = serializers.SerializerMethodField()
    is_reschedulable = serializers.SerializerMethodField()

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
            "cancellation_reason",
            "cancelled_at",
            "reschedule_required",
            "cancellation_cutoff",
            "is_cancellable",
            "is_reschedulable",
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

    def get_cancellation_cutoff(self, obj: Appointment) -> Optional[str]:
        from .services import get_appointment_cancellation_cutoff
        try:
            cutoff = get_appointment_cancellation_cutoff(obj)
            return cutoff.isoformat()
        except Exception:
            return None

    def get_is_cancellable(self, obj: Appointment) -> bool:
        from .services import check_patient_cancellation_eligibility
        try:
            eligible, _, _ = check_patient_cancellation_eligibility(obj)
            return eligible
        except Exception:
            return False

    def get_is_reschedulable(self, obj: Appointment) -> bool:
        from .services import check_patient_rescheduling_eligibility
        try:
            eligible, _, _ = check_patient_rescheduling_eligibility(obj)
            return eligible
        except Exception:
            return False


class AppointmentCancelRequestSerializer(serializers.Serializer):
    """Payload for patient or clinic cancellation."""
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=1000, default=""
    )


class AppointmentRescheduleRequestSerializer(serializers.Serializer):
    """
    Validates input parameters for rescheduling an appointment.
    Accepts either 'start_at' (ISO datetime) or both 'date' and 'time'.
    Doctor, clinic, fee, and patient identity cannot be altered by client payload.
    """
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    date = serializers.DateField(required=False, allow_null=True)
    time = serializers.TimeField(required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=1000, default=""
    )

    def validate(self, attrs):
        start_at = attrs.get("start_at")
        req_date = attrs.get("date")
        req_time = attrs.get("time")

        if not start_at and not (req_date and req_time):
            raise serializers.ValidationError(
                "Either 'start_at' (ISO datetime) or both 'date' and 'time' must be provided."
            )

        # Context appointment if provided
        appointment = self.context.get("appointment")
        if not start_at and req_date and req_time:
            tz_name = (
                appointment.clinic.timezone
                if appointment and appointment.clinic
                else "Asia/Kolkata"
            )
            try:
                clinic_tz = ZoneInfo(tz_name)
            except Exception:
                clinic_tz = ZoneInfo("Asia/Kolkata")

            combined_local = datetime.combine(req_date, req_time, tzinfo=clinic_tz)
            attrs["start_at"] = combined_local

        if attrs.get("start_at") and not timezone.is_aware(attrs["start_at"]):
            raise serializers.ValidationError("Provided appointment start timestamp must be timezone-aware.")

        return attrs


class AppointmentReportUnavailabilityRequestSerializer(serializers.Serializer):
    """Payload for doctor or clinic reporting unavailability on an appointment."""
    reason = serializers.CharField(
        required=True, min_length=3, max_length=1000, error_messages={
            "required": "A reason for reporting doctor or clinic unavailability must be documented."
        }
    )
    action = serializers.ChoiceField(
        choices=["RESCHEDULE_REQUIRED", "CANCEL"],
        default="RESCHEDULE_REQUIRED",
    )


class AppointmentHistorySerializer(serializers.ModelSerializer):
    """
    Read-only audit history representation for an appointment.
    """
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import AppointmentHistory
        model = AppointmentHistory
        fields = [
            "id",
            "appointment_id",
            "event_type",
            "previous_status",
            "new_status",
            "previous_start_at",
            "previous_end_at",
            "new_start_at",
            "new_end_at",
            "actor_id",
            "actor_name",
            "actor_role",
            "reason",
            "is_exception",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str:
        if not obj.actor:
            return "System"
        full = f"{obj.actor.first_name} {obj.actor.last_name}".strip()
        return full or obj.actor.email

